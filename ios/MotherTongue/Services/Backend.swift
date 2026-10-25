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
    /// The thread whose id starts with this family code (4 to 6 hex characters), any pairing state.
    func findThread(code: String) async throws -> ChatThread?
    func claimThread(id: UUID, familyId: UUID) async throws -> ChatThread
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

    /// Lowest and highest uuid strings starting with `code`, nil unless it is 1 to 32 hex characters.
    static func range(prefix code: String) -> (lo: String, hi: String)? {
        let hex = code.lowercased()
        guard (1...32).contains(hex.count), hex.allSatisfy(\.isHexDigit) else { return nil }
        func dashed(_ pad: Character) -> String {
            let s = Array(hex + String(repeating: pad, count: 32 - hex.count))
            return [0..<8, 8..<12, 12..<16, 16..<20, 20..<32].map { String(s[$0]) }.joined(separator: "-")
        }
        return (dashed("0"), dashed("f"))
    }
}
