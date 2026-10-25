import Foundation

/// Canned, offline backend so the UI can be built and screenshotted with no network.
@MainActor
final class DemoBackend: Backend {
    static let elder = Profile(id: UUID(uuidString: "11111111-1111-1111-1111-111111111111")!, name: "Margaret", role: .elder, lang: "es", voiceId: "demo")
    static let family = Profile(id: UUID(uuidString: "22222222-2222-2222-2222-222222222222")!, name: "Angel", role: .family, lang: "en", voiceId: "demo")
    static let thread = ChatThread(id: UUID(uuidString: "a1b2c3d4-0000-4000-8000-000000000001")!, elderId: elder.id, familyId: family.id)

    private var messages: [Message]
    private var continuation: AsyncStream<Void>.Continuation?
    private var replyIndex = 0

    init() {
        messages = Self.seed()
    }

    func createProfile(name: String, role: Role, lang: String) async throws -> Profile {
        var p = role == .elder ? Self.elder : Self.family
        p.name = name.isEmpty ? p.name : name
        p.lang = lang
        return p
    }

    func fetchProfile(id: UUID) async throws -> Profile? {
        [Self.elder, Self.family].first { $0.id == id }
    }

    func createThread(familyId: UUID) async throws -> ChatThread { Self.thread }
    func fetchThread(id: UUID) async throws -> ChatThread? { Self.thread }

    func openThreads() async throws -> [OpenThread] {
        [OpenThread(thread: Self.thread, family: Self.family)]
    }

    func joinThread(id: UUID, elderId: UUID) async throws -> ChatThread { Self.thread }

    func findThread(code: String) async throws -> ChatThread? {
        Self.thread.code.hasPrefix(code.uppercased()) ? Self.thread : nil
    }

    func claimThread(id: UUID, familyId: UUID) async throws -> ChatThread { Self.thread }

    func fetchMessages(threadId: UUID) async throws -> [Message] { messages }

    func uploadAudio(path: String, fileURL: URL?) async throws {
        try await Task.sleep(for: .milliseconds(400))
    }

    func insertMessage(_ m: NewMessage) async throws -> Message {
        let row = Message(id: m.id, threadId: m.threadId, senderId: m.senderId, sourceLang: m.sourceLang, targetLang: m.targetLang, originalPath: m.originalPath, status: .uploaded, createdAt: Message.timestamp(), replyTo: m.replyTo)
        messages.append(row)
        continuation?.yield()
        return row
    }

    func processMessage(id: UUID) async throws -> Message? {
        guard let i = messages.firstIndex(where: { $0.id == id }) else { return nil }
        try await Task.sleep(for: .milliseconds(600))
        messages[i].status = .processing
        continuation?.yield()
        try await Task.sleep(for: .seconds(2))
        let fromElder = messages[i].senderId == Self.elder.id
        let pool = fromElder ? Self.elderReplies : Self.familyReplies
        let reply = pool[replyIndex % pool.count]
        replyIndex += 1
        messages[i].transcript = reply.transcript
        messages[i].translation = reply.translation
        messages[i].culturalNotes = reply.notes
        messages[i].askAbout = reply.ask
        messages[i].status = .ready
        continuation?.yield()
        return messages[i]
    }

    func enrollVoice(profileId: UUID, samplePath: String) async throws -> String? {
        try await Task.sleep(for: .seconds(1.5))
        return "demo"
    }

    func messageChanges(threadId: UUID) async throws -> AsyncStream<Void> {
        AsyncStream { continuation in self.continuation = continuation }
    }

    func stopListening() async {
        continuation?.finish()
        continuation = nil
    }

    private struct Reply {
        var transcript: String
        var translation: String
        var notes: [CulturalNote] = []
        var ask: [String] = []
    }

    private static let elderReplies = [
        Reply(transcript: "Claro que sí, mijo. Te enseño todo, desde la masa hasta la salsa de mi abuela.",
              translation: "Of course, mijo. I will teach you everything, from the masa to my grandmother's salsa.",
              notes: [CulturalNote(term: "mijo", note: "Short for mi hijo, my son. A tender name for any boy in the family.")],
              ask: ["Ask her what made her grandmother's salsa special"])
    ]

    private static let familyReplies = [
        Reply(transcript: "I love you grandma. Tell me more stories when I visit.",
              translation: "Te quiero, abuela. Cuéntame más historias cuando te visite.")
    ]

    /// `Resources/demo-stories.json`, the same six stories the Hearth demo tells.
    private struct DemoFile: Decodable {
        struct DemoScene: Decodable {
            var image: String
            var text_es: String?
            var text_en: String?
            var prompt: String?
            var t_en: [Double]?
            var t_es: [Double]?
        }
        struct DemoStory: Decodable {
            var id: String
            var days_ago: Int
            var title: String
            var title_es: String
            var transcript: String
            var translation: String
            var ask_about: [String]?
            var scenes: [DemoScene]
        }
        struct DemoReply: Decodable {
            var after_story: String
            var minutes_after: Double
            var text_en: String
            var translation_es: String
            var title: String?
            var title_es: String?
            var scenes: [DemoScene]?
        }
        var stories: [DemoStory]
        var replies: [DemoReply]
    }

    static let audioPrefix = "demo-audio/"

    /// Bundle URL for a seeded message's narration path, nil when the file was never generated.
    static func bundledAudio(_ path: String?) -> URL? {
        guard let path, path.hasPrefix(audioPrefix) else { return nil }
        return Bundle.main.url(forResource: String(path.dropFirst(audioPrefix.count)), withExtension: "mp3")
    }

    private static func seed() -> [Message] {
        guard let url = Bundle.main.url(forResource: "demo-stories", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let file = try? JSONDecoder().decode(DemoFile.self, from: data) else { return [] }
        let t = thread.id
        let cal = Calendar.current
        func day(_ n: Int) -> Date {
            // Today's story landed an hour ago so its reply, half an hour later, is still in the past.
            n == 0 ? .now.addingTimeInterval(-60 * 60)
                : cal.startOfDay(for: .now.addingTimeInterval(-Double(n) * 86_400)).addingTimeInterval(15 * 3600)
        }
        // audio names the bundled ElevenLabs narration, Resources/DemoAudio/{audio}-{es|en}.mp3.
        // AppSession resolves the demo-audio/ paths from the bundle and falls back to speech.
        func msg(_ n: Int, from: Profile, at date: Date, transcript: String, translation: String, ask: [String] = [], story: Story? = nil, audio: String) -> Message {
            let id = UUID(uuidString: String(format: "00000000-0000-4000-8000-%012d", n))!
            let to = from.role == .elder ? family : elder
            return Message(id: id, threadId: t, senderId: from.id, sourceLang: from.lang, targetLang: to.lang,
                           originalPath: "\(Self.audioPrefix)\(audio)-\(from.lang)", transcript: transcript, translation: translation,
                           translatedPath: "\(Self.audioPrefix)\(audio)-\(to.lang)", culturalNotes: [], askAbout: ask, story: story, status: .ready,
                           createdAt: Message.timestamp(date))
        }
        var out: [Message] = []
        var dates: [String: Date] = [:]
        func scenes(_ list: [DemoFile.DemoScene]) -> [StoryScene] {
            list.map {
                StoryScene(start: $0.t_en?.first, end: $0.t_en?.last, textEs: $0.text_es, textEn: $0.text_en, prompt: $0.prompt,
                           imagePath: "demo/scene-\($0.image)", tEn: $0.t_en, tEs: $0.t_es)
            }
        }
        for (i, s) in file.stories.enumerated() {
            let list = scenes(s.scenes)
            let story = Story(title: s.title, imagePaths: list.first?.imagePath.map { [$0] }, titleEs: s.title_es,
                              status: "ready", scenes: list)
            let date = day(s.days_ago)
            dates[s.id] = date
            out.append(msg(i + 1, from: elder, at: date, transcript: s.transcript, translation: s.translation,
                           ask: s.ask_about ?? [], story: story, audio: s.id))
        }
        for (i, r) in file.replies.enumerated() {
            let date = (dates[r.after_story] ?? .now).addingTimeInterval(r.minutes_after * 60)
            let story = r.title == nil && r.scenes == nil ? nil : Story(title: r.title, titleEs: r.title_es, status: "ready", scenes: r.scenes.map(scenes))
            out.append(msg(file.stories.count + i + 1, from: family, at: date, transcript: r.text_en, translation: r.translation_es,
                           story: story, audio: "r\(i + 1)"))
        }
        #if DEBUG
        // Screenshot aid: `-pendingStory YES` makes today's story a film still being made.
        if UserDefaults.standard.bool(forKey: "pendingStory"), let i = out.firstIndex(where: { $0.senderId == elder.id && $0.date > day(1) }) {
            out[i].story?.status = "generating"
            out[i].createdAt = Message.timestamp()
        }
        #endif
        return out.sorted { $0.date < $1.date }
    }
}
