import Foundation

enum Role: String, Codable, CaseIterable, Sendable {
    case elder, family
}

struct Profile: Codable, Identifiable, Hashable, Sendable {
    var id: UUID
    var name: String
    var role: Role
    var lang: String
    var voiceId: String?

    enum CodingKeys: String, CodingKey {
        case id, name, role, lang
        case voiceId = "voice_id"
    }
}

struct ChatThread: Codable, Identifiable, Hashable, Sendable {
    var id: UUID
    var elderId: UUID?
    var familyId: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case elderId = "elder_id"
        case familyId = "family_id"
    }

    var code: String { String(id.uuidString.prefix(6)).uppercased() }
}

struct CulturalNote: Codable, Hashable, Sendable {
    var term: String
    var note: String
}

struct Story: Codable, Hashable, Sendable {
    var title: String?
    var imagePaths: [String]?
    var videoPath: String? = nil
    var thumbPath: String? = nil
    var titleEs: String? = nil
    var prompt: String? = nil
    var status: String? = nil
    var scenes: [StoryScene]? = nil

    enum CodingKeys: String, CodingKey {
        case title, prompt, status, scenes
        case imagePaths = "image_paths"
        case videoPath = "video_path"
        case thumbPath = "thumb_path"
        case titleEs = "title_es"
    }

    init(title: String? = nil, imagePaths: [String]? = nil, videoPath: String? = nil, thumbPath: String? = nil,
         titleEs: String? = nil, prompt: String? = nil, status: String? = nil, scenes: [StoryScene]? = nil) {
        self.title = title
        self.imagePaths = imagePaths
        self.videoPath = videoPath
        self.thumbPath = thumbPath
        self.titleEs = titleEs
        self.prompt = prompt
        self.status = status
        self.scenes = scenes
    }

    /// Tolerant: a malformed `scenes` entry drops the scenes, never the story.
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        title = try? c.decodeIfPresent(String.self, forKey: .title)
        imagePaths = try? c.decodeIfPresent([String].self, forKey: .imagePaths)
        videoPath = try? c.decodeIfPresent(String.self, forKey: .videoPath)
        thumbPath = try? c.decodeIfPresent(String.self, forKey: .thumbPath)
        titleEs = try? c.decodeIfPresent(String.self, forKey: .titleEs)
        prompt = try? c.decodeIfPresent(String.self, forKey: .prompt)
        status = try? c.decodeIfPresent(String.self, forKey: .status)
        scenes = try? c.decodeIfPresent([StoryScene].self, forKey: .scenes)
    }

    /// Scenes with `start` and `end` filled in. Missing times come from where each beat's English
    /// sits in the translation, in UTF-16 units of the unmarked text, the same units speech progress uses.
    func timedScenes(translation: String?) -> [StoryScene] {
        guard var out = scenes, !out.isEmpty else { return [] }
        if out.allSatisfy({ $0.start != nil }) {
            for i in out.indices where out[i].end == nil {
                out[i].end = i + 1 < out.count ? out[i + 1].start : 1
            }
            return out
        }
        if out.allSatisfy({ ($0.tEn?.count ?? 0) == 2 }) {
            for i in out.indices {
                if let t = out[i].tEn, t.count == 2 {
                    out[i].start = t[0]
                    out[i].end = t[1]
                }
            }
            return out
        }
        let full = (translation ?? "").unmarked as NSString
        let total = Double(max(1, full.length))
        var cursor = 0
        var starts: [Double?] = []
        for scene in out {
            guard let text = scene.textEn?.unmarked, !text.isEmpty, cursor < full.length else { starts.append(nil); continue }
            let r = full.range(of: text, range: NSRange(location: cursor, length: full.length - cursor))
            if r.location == NSNotFound { starts.append(nil); continue }
            starts.append(Double(r.location) / total)
            cursor = r.location + r.length
        }
        let even = starts.contains(nil) || starts.first! != 0
        for i in out.indices {
            let start = even ? Double(i) / Double(out.count) : starts[i]!
            out[i].start = out[i].start ?? start
        }
        for i in out.indices {
            out[i].end = out[i].end ?? (i + 1 < out.count ? out[i + 1].start : 1)
        }
        return out
    }
}

/// One beat of a story: its words in both languages, its timing as fractions of the narration, and its film.
struct StoryScene: Codable, Hashable, Sendable {
    var start: Double?
    var end: Double?
    var textEs: String?
    var textEn: String?
    var prompt: String?
    var videoPath: String?
    var thumbPath: String?
    var imagePath: String?
    var tEn: [Double]?
    var tEs: [Double]?

    enum CodingKeys: String, CodingKey {
        case start, end, prompt
        case tEn = "t_en"
        case tEs = "t_es"
        case textEs = "text_es"
        case textEn = "text_en"
        case videoPath = "video_path"
        case thumbPath = "thumb_path"
        case imagePath = "image_path"
    }

    init(start: Double? = nil, end: Double? = nil, textEs: String? = nil, textEn: String? = nil, prompt: String? = nil,
         videoPath: String? = nil, thumbPath: String? = nil, imagePath: String? = nil, tEn: [Double]? = nil, tEs: [Double]? = nil) {
        self.start = start
        self.end = end
        self.textEs = textEs
        self.textEn = textEn
        self.prompt = prompt
        self.videoPath = videoPath
        self.thumbPath = thumbPath
        self.imagePath = imagePath
        self.tEn = tEn
        self.tEs = tEs
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        start = try? c.decodeIfPresent(Double.self, forKey: .start)
        end = try? c.decodeIfPresent(Double.self, forKey: .end)
        textEs = try? c.decodeIfPresent(String.self, forKey: .textEs)
        textEn = try? c.decodeIfPresent(String.self, forKey: .textEn)
        prompt = try? c.decodeIfPresent(String.self, forKey: .prompt)
        videoPath = try? c.decodeIfPresent(String.self, forKey: .videoPath)
        thumbPath = try? c.decodeIfPresent(String.self, forKey: .thumbPath)
        imagePath = try? c.decodeIfPresent(String.self, forKey: .imagePath)
        tEn = try? c.decodeIfPresent([Double].self, forKey: .tEn)
        tEs = try? c.decodeIfPresent([Double].self, forKey: .tEs)
    }

    var hasMedia: Bool { videoPath != nil || imagePath != nil || thumbPath != nil }

    /// Index of the last scene whose start is at or below `progress`.
    static func index(in scenes: [StoryScene], at progress: Double) -> Int {
        scenes.lastIndex { ($0.start ?? 0) <= progress + 0.0001 } ?? 0
    }
}

enum MessageStatus: String, Codable, Sendable {
    case uploaded, processing, ready, error

    var isPending: Bool { self == .uploaded || self == .processing }
}

struct Message: Codable, Identifiable, Hashable, Sendable {
    var id: UUID
    var threadId: UUID
    var senderId: UUID
    var sourceLang: String
    var targetLang: String
    var originalPath: String
    var transcript: String?
    var translation: String?
    var translatedPath: String?
    var culturalNotes: [CulturalNote]?
    var askAbout: [String]?
    var story: Story?
    var status: MessageStatus
    var error: String?
    var createdAt: String?
    var heardAt: String?
    var replyTo: UUID? = nil

    enum CodingKeys: String, CodingKey {
        case id, transcript, translation, story, status, error
        case replyTo = "reply_to"
        case threadId = "thread_id"
        case senderId = "sender_id"
        case sourceLang = "source_lang"
        case targetLang = "target_lang"
        case originalPath = "original_path"
        case translatedPath = "translated_path"
        case culturalNotes = "cultural_notes"
        case askAbout = "ask_about"
        case createdAt = "created_at"
        case heardAt = "heard_at"
    }

    var date: Date {
        guard let createdAt else { return .now }
        return Self.parse(createdAt) ?? .now
    }

    nonisolated(unsafe) private static let isoFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()
    nonisolated(unsafe) private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    static func parse(_ s: String) -> Date? {
        isoFractional.date(from: s) ?? iso.date(from: s)
    }

    static func timestamp(_ date: Date = .now) -> String {
        isoFractional.string(from: date)
    }
}

struct NewMessage: Encodable, Sendable {
    var id: UUID
    var threadId: UUID
    var senderId: UUID
    var sourceLang: String
    var targetLang: String
    var originalPath: String
    var status: MessageStatus
    var replyTo: UUID? = nil

    enum CodingKeys: String, CodingKey {
        case id, status
        case replyTo = "reply_to"
        case threadId = "thread_id"
        case senderId = "sender_id"
        case sourceLang = "source_lang"
        case targetLang = "target_lang"
        case originalPath = "original_path"
    }
}
