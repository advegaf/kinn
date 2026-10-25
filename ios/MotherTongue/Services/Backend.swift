import Foundation

struct OpenThread: Identifiable, Hashable, Sendable {
    var thread: ChatThread
    var family: Profile?
    var id: UUID { thread.id }
}

@MainActor
protocol Backend: AnyObject {
    func createProfile(name: String, role: Role, lang: String) async throws -> Profile
    func fetchProfile(id: UUID) async throws -> Profile?
    func createThread(familyId: UUID) async throws -> ChatThread
    func fetchThread(id: UUID) async throws -> ChatThread?
    func openThreads() async throws -> [OpenThread]
    func joinThread(id: UUID, elderId: UUID) async throws -> ChatThread
    func fetchMessages(threadId: UUID) async throws -> [Message]
    func uploadAudio(path: String, fileURL: URL?) async throws
    func insertMessage(_ message: NewMessage) async throws -> Message
    func processMessage(id: UUID) async throws -> Message?
    func enrollVoice(profileId: UUID, samplePath: String) async throws -> String?
    /// Yields each time a message in the thread changes. Throws if the subscription cannot be set up.
    func messageChanges(threadId: UUID) async throws -> AsyncStream<Void>
    func stopListening() async
}

extension UUID {
    var lower: String { uuidString.lowercased() }
}
