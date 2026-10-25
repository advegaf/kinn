import SwiftUI

/// The earlier pages: every story by month, newest first, each with its replies in the order they were sent.
struct ArchiveView: View {
    var open: (UUID) -> Void
    var back: () -> Void
    var compose: () -> Void

    @Environment(AppSession.self) private var session

    private struct Thread: Identifiable {
        let root: Message
        let replies: [Message]
        var id: UUID { root.id }
    }

    private struct Month: Identifiable {
        let start: Date
        var threads: [Thread]
        var id: Date { start }
    }

    private var months: [Month] {
        let ready = session.messages.filter { $0.status == .ready }
        let byId = Dictionary(ready.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        func root(_ m: Message) -> Message {
            var top = m
            var seen: Set<UUID> = [m.id]
            while let up = top.replyTo, let parent = byId[up], seen.insert(up).inserted { top = parent }
            return top
        }
        let threads = Dictionary(grouping: ready) { root($0).id }
            .compactMap { id, rows -> Thread? in
                guard let top = byId[id] else { return nil }
                return Thread(root: top, replies: rows.filter { $0.id != id }.sorted { $0.date < $1.date })
            }
            .sorted { $0.root.date > $1.root.date }
        var out: [Month] = []
        for t in threads {
            let start = Almanac.calendar.dateInterval(of: .month, for: t.root.date)?.start ?? t.root.date
            if out.last?.start == start { out[out.count - 1].threads.append(t) } else { out.append(Month(start: start, threads: [t])) }
        }
        return out
    }

    var body: some View {
        let months = months
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                BackButton(action: back)
                head
                    .padding(.top, 8)
                if months.isEmpty {
                    FirstLoad(opening: "Opening the archive.", failed: "The archive could not load. Check the connection.") { empty }
                        .padding(.top, 32)
                }
                ForEach(months) { month in
                    monthHead(month.start)
                        .padding(.top, 40)
                    ForEach(month.threads) { thread in
                        row(thread)
                    }
                }
            }
            .padding(.horizontal, 30)
            .padding(.top, 16)
            .padding(.bottom, 40)
        }
        .scrollIndicators(.hidden)
        .background { PaperCanvas() }
    }

    private var head: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("Archive")
                .font(.serif(28, relativeTo: .title))
                .foregroundStyle(Color.ink)
            Text("Every story from \(session.partnerName), with your replies")
                .font(.serif(17))
                .foregroundStyle(Color.soft)
        }
    }

    private var empty: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("No stories yet. When \(session.partnerName) tells one on her Hearth, it lands here with your replies.")
                .font(.serif(19))
                .foregroundStyle(Color.soft)
            Button("Write her a note", action: compose)
                .font(.serif(19))
                .foregroundStyle(Color.ink)
                .dottedUnderline(.ink)
                .buttonStyle(PressStyle())
                .tapTarget()
        }
    }

    private func monthHead(_ start: Date) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            Text(Almanac.month(start))
                .font(.serif(44, relativeTo: .largeTitle))
                .tracking(-0.9)
                .foregroundStyle(Color.ink)
            Text(String(Almanac.calendar.component(.year, from: start)))
                .font(.serif(20))
                .monospacedDigit()
                .foregroundStyle(Color.sub)
        }
        .padding(.bottom, 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .overlay(alignment: .bottom) { Hairline() }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
    }

    private func row(_ thread: Thread) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Button { open(thread.root.id) } label: {
                HStack(alignment: .top, spacing: 0) {
                    Text("\(Almanac.dayNumber(thread.root.date))")
                        .font(.serif(22))
                        .monospacedDigit()
                        .foregroundStyle(Color.sub)
                        .frame(width: 44, alignment: .leading)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(Almanac.titleEn(thread.root))
                            .font(.serif(19))
                            .foregroundStyle(Color.ink)
                        Text(Almanac.titleEs(thread.root))
                            .font(.serif(15))
                            .foregroundStyle(Color.sub)
                        Text(session.isMine(thread.root) ? "You sent this" : Almanac.day(thread.root.date))
                            .font(.serif(15))
                            .foregroundStyle(Color.soft)
                    }
                    .multilineTextAlignment(.leading)
                    Spacer(minLength: 16)
                    if let path = thread.root.story?.coverPath {
                        StoryImage(path: path)
                            .frame(width: 64, height: 64)
                            .clipShape(.rect(cornerRadius: 3))
                            .overlay { RoundedRectangle(cornerRadius: 3).strokeBorder(.black.opacity(0.1), lineWidth: 1) }
                            .accessibilityHidden(true)
                    }
                }
                .padding(.vertical, 12)
                .contentShape(.rect)
            }
            .buttonStyle(PressStyle())
            ForEach(thread.replies) { reply in
                replyRow(reply)
            }
        }
        .padding(.bottom, thread.replies.isEmpty ? 0 : 8)
        .overlay(alignment: .bottom) { Hairline() }
    }

    private func replyRow(_ m: Message) -> some View {
        Button { open(m.id) } label: {
            VStack(alignment: .leading, spacing: 2) {
                Text(Almanac.titleEn(m))
                    .font(.serif(17))
                    .foregroundStyle(Color.ink)
                Text(session.isMine(m) ? "You wrote back, \(Almanac.day(m.date))" : "\(session.partnerName) wrote back, \(Almanac.day(m.date))")
                    .font(.serif(15))
                    .foregroundStyle(Color.soft)
            }
            .multilineTextAlignment(.leading)
            .padding(.leading, 12)
            .padding(.vertical, 8)
            .frame(maxWidth: .infinity, minHeight: 44, alignment: .leading)
            .overlay(alignment: .leading) { Rectangle().fill(Color.rule).frame(width: 1) }
            .contentShape(.rect)
        }
        .buttonStyle(PressStyle())
        .padding(.leading, 44)
    }
}
