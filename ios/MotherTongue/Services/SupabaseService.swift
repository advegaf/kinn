import Foundation
import Supabase

@MainActor
final class SupabaseService: Backend {
    private let client: SupabaseClient
    private var channel: RealtimeChannelV2?

    init?() {
        guard let url = AppConfig.supabaseURL, AppConfig.isConfigured else { return nil }
        client = SupabaseClient(supabaseURL: url, supabaseKey: AppConfig.anonKey)
    }

    func createProfile(name: String, role: Role, lang: String) async throws -> Profile {
        struct Row: Encodable { let name: String; let role: Role; let lang: String }
        return try await client.from("profiles")
            .insert(Row(name: name, role: role, lang: lang))
            .select()
            .single()
            .execute()
            .value
    }

    func fetchProfile(id: UUID) async throws -> Profile? {
        let rows: [Profile] = try await client.from("profiles").select().eq("id", value: id.lower).limit(1).execute().value
        return rows.first
    }

    func createThread(familyId: UUID) async throws -> ChatThread {
        struct Row: Encodable { let family_id: String }
        return try await client.from("threads")
            .insert(Row(family_id: familyId.lower))
            .select()
            .single()
            .execute()
            .value
    }

    func fetchThread(id: UUID) async throws -> ChatThread? {
        let rows: [ChatThread] = try await client.from("threads").select().eq("id", value: id.lower).limit(1).execute().value
        return rows.first
    }

    func openThreads() async throws -> [OpenThread] {
        let threads: [ChatThread] = try await client.from("threads")
            .select()
            .is("elder_id", value: nil)
            .order("created_at", ascending: false)
            .limit(30)
            .execute()
            .value
        let ids = threads.compactMap { $0.familyId?.lower }
        var families: [UUID: Profile] = [:]
        if !ids.isEmpty {
            let profiles: [Profile] = try await client.from("profiles").select().in("id", values: ids).execute().value
            for p in profiles { families[p.id] = p }
        }
        return threads.map { OpenThread(thread: $0, family: $0.familyId.flatMap { families[$0] }) }
    }

    func joinThread(id: UUID, elderId: UUID) async throws -> ChatThread {
        struct Row: Encodable { let elder_id: String }
        return try await client.from("threads")
            .update(Row(elder_id: elderId.lower))
            .eq("id", value: id.lower)
            .select()
            .single()
            .execute()
            .value
    }

    func fetchMessages(threadId: UUID) async throws -> [Message] {
        try await client.from("messages")
            .select()
            .eq("thread_id", value: threadId.lower)
            .order("created_at", ascending: true)
            .limit(200)
            .execute()
            .value
    }

    func uploadAudio(path: String, fileURL: URL?) async throws {
        guard let fileURL else { throw URLError(.fileDoesNotExist) }
        let data = try Data(contentsOf: fileURL)
        try await client.storage.from("audio").upload(path, data: data, options: FileOptions(contentType: "audio/mp4", upsert: true))
    }

    func insertMessage(_ message: NewMessage) async throws -> Message {
        try await client.from("messages").insert(message).select().single().execute().value
    }

    func processMessage(id: UUID) async throws -> Message? {
        struct Body: Encodable { let message_id: String }
        return try await client.functions.invoke(
            "process-message",
            options: FunctionInvokeOptions(body: Body(message_id: id.lower))
        ) { @Sendable data, _ in try? JSONDecoder().decode(Message.self, from: data) }
    }

    func enrollVoice(profileId: UUID, samplePath: String) async throws -> String? {
        struct Body: Encodable { let profile_id: String; let sample_path: String }
        struct Response: Decodable { let voice_id: String? }
        let response: Response = try await client.functions.invoke(
            "enroll-voice",
            options: FunctionInvokeOptions(body: Body(profile_id: profileId.lower, sample_path: samplePath))
        )
        return response.voice_id
    }

    func messageChanges(threadId: UUID) async throws -> AsyncStream<Void> {
        await stopListening()
        let channel = client.channel("messages-\(threadId.lower)")
        let changes = channel.postgresChange(AnyAction.self, schema: "public", table: "messages", filter: .eq("thread_id", value: threadId.lower))
        try await channel.subscribeWithError()
        self.channel = channel
        return AsyncStream { continuation in
            let task = Task {
                for await _ in changes { continuation.yield() }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    func stopListening() async {
        if let channel { await client.removeChannel(channel) }
        channel = nil
    }
}
