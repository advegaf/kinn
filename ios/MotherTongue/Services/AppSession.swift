import Foundation
import Observation

@Observable
@MainActor
final class AppSession {
    private(set) var backend: Backend?
    private(set) var isDemo = false
    var profile: Profile?
    var thread: ChatThread?
    var partner: Profile?
    private(set) var messages: [Message] = []
    var lastError: String?
    /// Increments when a new ready message from the partner arrives.
    private(set) var arrivals = 0
    private(set) var heardIds: Set<UUID> = []

    let recorder = AudioRecorder()
    let player = AudioPlayer()

    private var localFiles: [UUID: URL] = [:]
    private var localOnly: Set<UUID> = []
    private var listenTask: Task<Void, Never>?
    private var pollTask: Task<Void, Never>?
    private var realtimeHealthy = false
    private let defaults = UserDefaults.standard

    init() {
        heardIds = Set((defaults.stringArray(forKey: StorageKeys.heardIds) ?? []).compactMap(UUID.init))
        configureBackend()
    }

    // MARK: Setup

    func configureBackend() {
        stopSync()
        let demo = defaults.bool(forKey: StorageKeys.demoMode)
        if demo != isDemo {
            profile = nil
            thread = nil
        }
        isDemo = demo
        backend = isDemo ? DemoBackend() : SupabaseService()
        messages = []
        localOnly = []
    }

    var role: Role { profile?.role ?? Role(rawValue: defaults.string(forKey: StorageKeys.role) ?? "") ?? .family }
    var myLang: String { profile?.lang ?? defaults.string(forKey: StorageKeys.lang) ?? (role == .elder ? "es" : "en") }
    var partnerLang: String { partner?.lang ?? (role == .elder ? "en" : "es") }
    var partnerName: String {
        if let name = partner?.name, !name.isEmpty { return name }
        return role == .elder ? "tu familia" : "Grandma"
    }

    /// Restores the persisted profile and thread, then starts syncing messages.
    func start() async {
        guard let backend else { return }
        do {
            if isDemo {
                profile = role == .elder ? DemoBackend.elder : DemoBackend.family
                if let name = defaults.string(forKey: StorageKeys.name), !name.isEmpty { profile?.name = name }
                thread = DemoBackend.thread
            } else {
                if profile == nil, let id = defaults.string(forKey: StorageKeys.profileId).flatMap(UUID.init) {
                    profile = try await backend.fetchProfile(id: id)
                }
                if let id = defaults.string(forKey: StorageKeys.threadId).flatMap(UUID.init) {
                    thread = try await backend.fetchThread(id: id)
                }
            }
            await loadPartner()
            await refresh()
            startSync()
        } catch {
            lastError = error.localizedDescription
        }
    }

    func loadPartner() async {
        guard let backend, let thread, let profile else { return }
        let partnerId = profile.role == .elder ? thread.familyId : thread.elderId
        guard let partnerId else { return }
        partner = try? await backend.fetchProfile(id: partnerId)
    }

    // MARK: Onboarding

    func createProfile(name: String, role: Role, lang: String) async throws {
        guard let backend else { throw SessionError.notConfigured }
        if let profile, profile.name == name, profile.role == role, profile.lang == lang { return }
        let p = try await backend.createProfile(name: name, role: role, lang: lang)
        profile = p
        defaults.set(p.id.uuidString, forKey: StorageKeys.profileId)
        thread = nil
        defaults.removeObject(forKey: StorageKeys.threadId)
    }

    func createThread() async throws {
        guard let backend, let profile else { throw SessionError.notConfigured }
        let t = try await backend.createThread(familyId: profile.id)
        setThread(t)
    }

    func openThreads() async throws -> [OpenThread] {
        guard let backend else { throw SessionError.notConfigured }
        return try await backend.openThreads()
    }

    func join(_ t: ChatThread) async throws {
        guard let backend, let profile else { throw SessionError.notConfigured }
        let joined = try await backend.joinThread(id: t.id, elderId: profile.id)
        setThread(joined)
    }

    /// Elder: joins a waiting family thread. Family: finds the thread by code and, when a family
    /// profile already holds it, becomes that profile; otherwise claims it.
    func join(code: String) async throws {
        let code = code.trimmingCharacters(in: .whitespaces).uppercased()
        guard code.count >= 4 else { throw SessionError.badCode }
        if role == .family {
            guard let backend, let me = profile else { throw SessionError.notConfigured }
            guard let found = try await backend.findThread(code: code) else { throw SessionError.badCode }
            if let fid = found.familyId, fid != me.id, let owner = try await backend.fetchProfile(id: fid), owner.role == .family {
                profile = owner
                defaults.set(owner.id.uuidString, forKey: StorageKeys.profileId)
                defaults.set(owner.name, forKey: StorageKeys.name)
                setThread(found)
            } else {
                setThread(try await backend.claimThread(id: found.id, familyId: me.id))
            }
            defaults.set("en", forKey: StorageKeys.lang)
            partner = nil
            await loadPartner()
            return
        }
        let open = try await openThreads()
        guard let match = open.first(where: { $0.thread.id.uuidString.uppercased().hasPrefix(code) }) else { throw SessionError.badCode }
        try await join(match.thread)
    }

    private func setThread(_ t: ChatThread) {
        thread = t
        defaults.set(t.id.uuidString, forKey: StorageKeys.threadId)
    }

    func enrollVoice(sample url: URL?) async throws {
        guard let backend, let profile else { throw SessionError.notConfigured }
        let path = "voices/\(profile.id.lower).m4a"
        if !isDemo { try await backend.uploadAudio(path: path, fileURL: url) }
        let voiceId = try await backend.enrollVoice(profileId: profile.id, samplePath: path)
        self.profile?.voiceId = voiceId
        defaults.set(true, forKey: StorageKeys.enrolled)
    }

    func reset() {
        stopSync()
        player.stop()
        for key in [StorageKeys.onboarded, StorageKeys.profileId, StorageKeys.threadId, StorageKeys.heardIds, StorageKeys.enrolled,
                    StorageKeys.lang, StorageKeys.role, StorageKeys.name] {
            defaults.removeObject(forKey: key)
        }
        profile = nil
        thread = nil
        partner = nil
        messages = []
        heardIds = []
    }

    // MARK: Messages

    func isMine(_ m: Message) -> Bool { m.senderId == profile?.id }

    var unheard: [Message] {
        messages.filter { !isMine($0) && $0.status == .ready && !heardIds.contains($0.id) }
    }

    var latestFromPartner: Message? {
        messages.last { !isMine($0) && $0.status == .ready }
    }

    var latestStoryImage: String? {
        messages.reversed().lazy.compactMap { $0.story?.scenes?.first?.imagePath ?? $0.story?.imagePaths?.first }.first
    }

    var hasPending: Bool { messages.contains { isMine($0) && $0.status.isPending } }

    func markHeard(_ id: UUID) {
        heardIds.insert(id)
        defaults.set(heardIds.map(\.uuidString), forKey: StorageKeys.heardIds)
    }

    func send(recording url: URL?, replyTo: UUID? = nil) async {
        guard let backend, let profile, let thread else {
            lastError = "Not connected to a family thread yet."
            return
        }
        let id = UUID()
        let path = "\(thread.id.lower)/\(id.lower).m4a"
        if let url { localFiles[id] = url }
        let draft = Message(id: id, threadId: thread.id, senderId: profile.id, sourceLang: profile.lang, targetLang: partnerLang,
                            originalPath: path, status: .uploaded, createdAt: Message.timestamp(), replyTo: replyTo)
        messages.append(draft)
        localOnly.insert(id)
        do {
            try await backend.uploadAudio(path: path, fileURL: url)
            let row = NewMessage(id: id, threadId: thread.id, senderId: profile.id, sourceLang: profile.lang,
                                 targetLang: partnerLang, originalPath: path, status: .uploaded, replyTo: replyTo)
            let inserted = try await backend.insertMessage(row)
            localOnly.remove(id)
            upsert(inserted)
        } catch {
            markLocalError(id, error.localizedDescription)
            return
        }
        do {
            if let updated = try await backend.processMessage(id: id) { upsert(updated) }
        } catch {
            await refresh()
            if let m = messages.first(where: { $0.id == id }), m.status == .uploaded {
                markLocalError(id, "Could not reach the translator. \(error.localizedDescription)")
            }
        }
        await refresh()
    }

    func retry(_ m: Message) async {
        guard let backend else { return }
        if let i = messages.firstIndex(where: { $0.id == m.id }) {
            messages[i].status = .uploaded
            messages[i].error = nil
        }
        if localOnly.contains(m.id) {
            messages.removeAll { $0.id == m.id }
            localOnly.remove(m.id)
            await send(recording: localFiles[m.id], replyTo: m.replyTo)
            return
        }
        if let updated = try? await backend.processMessage(id: m.id) { upsert(updated) }
        await refresh()
    }

    private func markLocalError(_ id: UUID, _ text: String) {
        guard let i = messages.firstIndex(where: { $0.id == id }) else { return }
        messages[i].status = .error
        messages[i].error = text
    }

    private func upsert(_ m: Message) {
        if let i = messages.firstIndex(where: { $0.id == m.id }) { messages[i] = m } else { messages.append(m) }
    }

    func refresh() async {
        guard let backend, let thread else { return }
        let server: [Message]
        do {
            server = try await backend.fetchMessages(threadId: thread.id)
            lastError = nil
        } catch {
            lastError = "Sync failed: \(error.localizedDescription)"
            return
        }
        let before = Dictionary(uniqueKeysWithValues: messages.map { ($0.id, $0.status) })
        let serverIds = Set(server.map(\.id))
        let pendingLocal = messages.filter { localOnly.contains($0.id) && !serverIds.contains($0.id) }
        let merged = (server + pendingLocal).sorted { $0.date < $1.date }
        let hadMessages = !messages.isEmpty
        messages = merged
        let arrived = merged.contains { m in
            !isMine(m) && m.status == .ready && before[m.id] != .ready
        }
        if arrived && hadMessages {
            arrivals += 1
            Haptics.arrival()
        }
        if partner == nil { await loadPartner() }
    }

    // MARK: Sync

    func startSync() {
        stopSync()
        guard let backend, let thread else { return }
        listenTask = Task { [weak self] in
            do {
                let stream = try await backend.messageChanges(threadId: thread.id)
                self?.realtimeHealthy = true
                for await _ in stream {
                    await self?.refresh()
                }
            } catch {
                self?.realtimeHealthy = false
            }
            self?.realtimeHealthy = false
        }
        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                let fast = !self.realtimeHealthy || self.hasPending
                try? await Task.sleep(for: .seconds(fast ? 2.5 : 15))
                if Task.isCancelled { return }
                await self.refresh()
            }
        }
    }

    func stopSync() {
        listenTask?.cancel()
        pollTask?.cancel()
        listenTask = nil
        pollTask = nil
        if let backend { Task { await backend.stopListening() } }
    }

    // MARK: Playback

    func translatedSource(_ m: Message) -> PlaybackSource? {
        let speech = m.translation.map { PlaybackSource.speech(text: $0.unmarked, lang: m.targetLang) }
        if isDemo, let url = DemoBackend.bundledAudio(m.translatedPath) { return .url(url, fallback: speech) }
        if !isDemo, let path = m.translatedPath, !path.isEmpty, let url = AppConfig.publicURL(bucket: "audio", path: path) { return .url(url, fallback: speech) }
        return speech
    }

    func originalSource(_ m: Message) -> PlaybackSource? {
        if let local = localFiles[m.id] { return .url(local) }
        if isDemo, let url = DemoBackend.bundledAudio(m.originalPath) { return .url(url) }
        let speech = m.transcript.map { PlaybackSource.speech(text: $0, lang: m.sourceLang) }
        if !isDemo, !m.originalPath.isEmpty, let url = AppConfig.publicURL(bucket: "audio", path: m.originalPath) { return .url(url, fallback: speech) }
        return speech
    }

    func imageURL(_ path: String) -> URL? {
        AppConfig.publicURL(bucket: "images", path: path)
    }

    func videoURL(_ path: String) -> URL? {
        AppConfig.publicURL(bucket: "videos", path: path)
    }
}

enum SessionError: LocalizedError {
    case notConfigured, badCode
    var errorDescription: String? {
        switch self {
        case .notConfigured: "The backend is not configured. Add Secrets.xcconfig or turn on demo mode."
        case .badCode: "No family found with that code."
        }
    }
}
