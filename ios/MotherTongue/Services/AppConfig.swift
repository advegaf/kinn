import Foundation

enum AppConfig {
    static var supabaseURL: URL? {
        guard let raw = Bundle.main.object(forInfoDictionaryKey: "SUPABASE_URL") as? String,
              raw.hasPrefix("http"), !raw.contains("YOUR-PROJECT") else { return nil }
        return URL(string: raw)
    }

    static var anonKey: String {
        (Bundle.main.object(forInfoDictionaryKey: "SUPABASE_ANON_KEY") as? String) ?? ""
    }

    static var isConfigured: Bool { supabaseURL != nil && !anonKey.isEmpty && anonKey != "YOUR-ANON-KEY" }

    static func publicURL(bucket: String, path: String) -> URL? {
        guard let base = supabaseURL else { return nil }
        var clean = path
        if clean.hasPrefix("\(bucket)/") { clean.removeFirst(bucket.count + 1) }
        return base.appending(path: "storage/v1/object/public/\(bucket)/\(clean)")
    }
}

enum StorageKeys {
    static let onboarded = "onboarded"
    static let profileId = "profileId"
    static let threadId = "threadId"
    static let name = "name"
    static let role = "role"
    static let lang = "lang"
    static let demoMode = "demoMode"
    static let shutterRemote = "shutterRemote"
    static let heardIds = "heardIds"
    static let enrolled = "enrolled"
}
