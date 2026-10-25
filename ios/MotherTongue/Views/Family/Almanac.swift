import SwiftUI

/// Calendar math and the date lines the almanac prints, in English.
enum Almanac {
    static let weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    static let calendar: Calendar = {
        var c = Calendar(identifier: .iso8601)
        c.timeZone = .current
        return c
    }()

    private static let formatters: [String: DateFormatter] = {
        var out: [String: DateFormatter] = [:]
        for (key, locale, format) in [
            ("month", "en_US", "LLLL"),
            ("day", "en_US", "EEEE d"),
            ("weekdayMonth", "en_US", "EEEE, MMMM"),
            ("monthYearEn", "en_US", "MMMM yyyy"),
            ("time", "en_US", "h:mm a")
        ] {
            let f = DateFormatter()
            f.locale = Locale(identifier: locale)
            f.dateFormat = format
            out[key] = f
        }
        return out
    }()

    private static func format(_ key: String, _ date: Date) -> String {
        formatters[key]?.string(from: date) ?? ""
    }

    /// "October"
    static func month(_ d: Date) -> String { format("month", d) }
    /// "Saturday 24"
    static func day(_ d: Date) -> String { format("day", d) }
    /// "Saturday, October"
    static func weekdayMonth(_ d: Date) -> String { format("weekdayMonth", d) }
    /// "2:48 PM"
    static func time(_ d: Date) -> String { format("time", d) }
    /// "October 2026, week 43"
    static func monthLine(_ d: Date) -> String {
        "\(format("monthYearEn", d)), week \(calendar.component(.weekOfYear, from: d))"
    }

    static func dayNumber(_ d: Date) -> Int { calendar.component(.day, from: d) }

    /// Monday through Sunday of the week holding `d`.
    static func week(of d: Date) -> [Date] {
        guard let start = calendar.dateInterval(of: .weekOfYear, for: d)?.start else { return [] }
        return (0..<7).compactMap { calendar.date(byAdding: .day, value: $0, to: start) }
    }

    /// The Spanish title, shown small under the English one. Falls back to the opening words.
    static func titleEs(_ m: Message) -> String {
        title(m.story?.titleEs, text(m, english: false), or: "traducci\u{F3}n pendiente")
    }

    static func titleEn(_ m: Message) -> String {
        title(m.story?.title, text(m, english: true), or: "A note to Margaret")
    }

    private static func text(_ m: Message, english: Bool) -> String {
        let own = m.sourceLang == "en" ? m.transcript : m.translation
        let other = m.sourceLang == "en" ? m.translation : m.transcript
        let first = english ? own : other
        let second = english ? other : own
        return [first, second].compactMap { $0 }.first { !$0.isEmpty } ?? ""
    }

    private static func title(_ story: String?, _ text: String, or empty: String) -> String {
        if let story, !story.isEmpty { return story }
        let words = openingWords(text)
        return words.isEmpty ? empty : words
    }

    private static func openingWords(_ text: String) -> String {
        let words = text.unmarked.split(separator: " ").prefix(4).joined(separator: " ")
        return words.trimmingCharacters(in: .punctuationCharacters)
    }

    /// Spoken length at about 2.5 words a second.
    static func duration(_ m: Message) -> TimeInterval {
        let words = (m.translation ?? m.transcript ?? "").split(separator: " ").count
        return max(4, Double(words) / 2.5)
    }

    /// The line quoted at the top of a reply: the marked run if there is one, else the last sentence,
    /// cut at a comma so it stays short.
    static func quote(_ m: Message) -> String {
        let text = m.translation ?? m.transcript ?? ""
        let parts = text.split(separator: "*", omittingEmptySubsequences: false)
        var line = parts.count > 2 ? String(parts[1]) : String(text.unmarked.split(separator: ".").last ?? "")
        line = line.trimmingCharacters(in: .whitespaces.union(.punctuationCharacters))
        if line.count > 45, let comma = line.prefix(45).lastIndex(of: ",") {
            line = String(line[..<comma])
        }
        let opens = text.unmarked.hasPrefix(line)
        return (opens ? "" : "\u{2026}") + line + "."
    }

    static func roman(_ i: Int) -> String {
        ["i", "ii", "iii", "iv", "v", "vi"][min(i, 5)]
    }
}

extension View {
    /// The diary's dotted 1 pt underline, sitting 5 pt under the baseline.
    func dottedUnderline(_ color: Color) -> some View {
        overlay(alignment: .bottom) {
            Line()
                .stroke(color, style: StrokeStyle(lineWidth: 1, dash: [1, 2]))
                .frame(height: 1)
                .offset(y: 1)
        }
    }
}

private struct Line: Shape {
    func path(in rect: CGRect) -> Path {
        Path { p in
            p.move(to: CGPoint(x: rect.minX, y: rect.midY))
            p.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
        }
    }
}

/// The oxblood bookmark: woven, with a swallowtail notch. The only mark for today.
struct Ribbon: View {
    var body: some View {
        Color.ribbon
            .overlay {
                Canvas { ctx, size in
                    var x: CGFloat = 0
                    while x < size.width {
                        ctx.fill(Path(CGRect(x: x, y: 0, width: 1, height: size.height)), with: .color(Color(hex: 0xFFECE0, opacity: 0.09)))
                        x += 2.5
                    }
                    var y: CGFloat = 0
                    while y < size.height {
                        ctx.fill(Path(CGRect(x: 0, y: y, width: size.width, height: 1)), with: .color(.black.opacity(0.11)))
                        y += 2
                    }
                }
            }
            .overlay {
                LinearGradient(stops: [.init(color: .black.opacity(0.14), location: 0), .init(color: .clear, location: 0.25),
                                       .init(color: .clear, location: 0.75), .init(color: .black.opacity(0.14), location: 1)],
                               startPoint: .leading, endPoint: .trailing)
            }
            .clipShape(Swallowtail())
            .frame(width: 17)
            .shadow(color: Color(hex: 0x28120A, opacity: 0.32), radius: 1, y: 3)
            .shadow(color: Color(hex: 0x28120A, opacity: 0.12), radius: 0, x: 1)
            .allowsHitTesting(false)
            .accessibilityHidden(true)
    }
}

private struct Swallowtail: Shape {
    func path(in r: CGRect) -> Path {
        Path { p in
            p.move(to: CGPoint(x: r.minX, y: r.minY))
            p.addLine(to: CGPoint(x: r.maxX, y: r.minY))
            p.addLine(to: CGPoint(x: r.maxX, y: r.maxY))
            p.addLine(to: CGPoint(x: r.midX, y: r.maxY - 9))
            p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
            p.closeSubpath()
        }
    }
}
