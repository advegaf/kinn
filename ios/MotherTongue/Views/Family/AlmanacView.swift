import SwiftUI

/// 01 the week: the month, this week's row with the ribbon on today, today's story, and the index.
struct AlmanacView: View {
    var open: (UUID) -> Void

    @Environment(AppSession.self) private var session

    /// Every ready note, hers and mine, newest first, minus the one featured above.
    private var others: [Message] {
        let featuredId = session.latestFromPartner?.id
        return session.messages.filter { $0.status == .ready && $0.id != featuredId }.reversed()
    }

    var body: some View {
        let now = Date.now
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                head
                Text(Almanac.month(now))
                    .font(.serif(66, relativeTo: .largeTitle))
                    .tracking(-1.65)
                    .foregroundStyle(Color.ink)
                    .padding(.top, 14)
                Text(Almanac.monthLine(now))
                    .font(.serif(20))
                    .foregroundStyle(Color.sub)
                    .padding(.top, -5)
                weekRow(now)
                    .padding(.top, 30)
                if let today = session.latestFromPartner {
                    featured(today)
                        .padding(.top, 26)
                } else {
                    empty.padding(.top, 26)
                }
                status
                index(others)
                    .padding(.top, 24)
            }
            .padding(.horizontal, 30)
            .padding(.top, 16)
            .padding(.bottom, 40)
        }
        .scrollClipDisabled()
        .mask { Rectangle().ignoresSafeArea(edges: .bottom) }
        .scrollIndicators(.hidden)
    }

    private var head: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("Kinn")
                .font(.serif(28, relativeTo: .title))
                .foregroundStyle(Color.ink)
            Text("To \(session.partnerName)\(session.isDemo ? ", Monterrey" : "")")
                .font(.serif(17))
                .foregroundStyle(Color.soft)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func weekRow(_ now: Date) -> some View {
        let days = Almanac.week(of: now)
        let todayIndex = days.firstIndex { Almanac.calendar.isDate($0, inSameDayAs: now) } ?? 0
        return HStack(spacing: 0) {
            ForEach(Array(days.enumerated()), id: \.offset) { i, day in
                let color: Color = i == todayIndex ? .ink : i < todayIndex ? .soft : .later
                VStack(spacing: 12) {
                    Text(Almanac.weekdays[i])
                        .font(.sans(12))
                        .foregroundStyle(i == todayIndex ? Color.ink : i < todayIndex ? Color.fog : Color.later)
                    Text("\(Almanac.dayNumber(day))")
                        .font(.serif(40))
                        .monospacedDigit()
                        .foregroundStyle(color)
                }
                .frame(maxWidth: .infinity)
                .accessibilityElement(children: .combine)
                .accessibilityAddTraits(i == todayIndex ? .isSelected : [])
            }
        }
        .padding(.top, 12)
        .padding(.bottom, 14)
        .overlay(alignment: .top) { Hairline() }
        .overlay(alignment: .bottom) { Hairline() }
        .overlay(alignment: .topLeading) {
            GeometryReader { geo in
                let column = geo.size.width / 7
                Ribbon()
                    .frame(height: 900)
                    .offset(x: column * (CGFloat(todayIndex) + 0.5) - 8.5, y: 8 - 900)
            }
        }
    }

    private func featured(_ m: Message) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Button { open(m.id) } label: {
                VStack(alignment: .leading, spacing: -2) {
                    Text(Almanac.titleEn(m))
                        .font(.serif(34, relativeTo: .title))
                        .tracking(-0.5)
                        .foregroundStyle(Color.ink)
                        .multilineTextAlignment(.leading)
                    Text(Almanac.titleEs(m))
                        .font(.serif(17))
                        .foregroundStyle(Color.sub)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(.rect)
            }
            .buttonStyle(PressStyle())
            .accessibilityIdentifier("almanac.featured")
            Text("\(Almanac.day(m.date)) at \(Almanac.time(m.date))")
                .font(.serif(17))
                .foregroundStyle(Color.soft)
                .padding(.top, 6)
            HStack(spacing: 18) {
                Button("Listen") { open(m.id) }
                    .accessibilityIdentifier("almanac.listen")
                    .font(.serif(19))
                    .foregroundStyle(Color.ink)
                    .dottedUnderline(.ink)
                let key = "o-\(m.id)"
                let playing = session.player.isPlaying && session.player.currentKey == key
                Button(playing ? "Stop her voice" : "Hear her original") {
                    if let src = session.originalSource(m) { session.player.toggle(src, key: key) }
                }
                .font(.serif(19))
                .foregroundStyle(Color.soft)
                .accessibilityIdentifier("almanac.original")
            }
            .buttonStyle(PressStyle())
            .frame(minHeight: 44)
            .padding(.top, 2)
        }
    }

    @ViewBuilder private var empty: some View {
        if !session.hasLoaded, session.lastError != nil {
            VStack(alignment: .leading, spacing: 4) {
                Text("This week could not load. Check the connection.")
                    .font(.serif(19))
                    .foregroundStyle(Color.soft)
                Button("Try again") { Task { await session.start() } }
                    .font(.serif(19))
                    .foregroundStyle(Color.ink)
                    .dottedUnderline(.ink)
                    .buttonStyle(PressStyle())
                    .tapTarget()
            }
        } else if !session.hasLoaded {
            Breathing {
                Text("Opening this week.")
                    .font(.serif(19))
                    .foregroundStyle(Color.soft)
            }
        } else {
            Text("Nothing from \(session.partnerName) yet. Her stories will land on this page.")
                .font(.serif(19))
                .foregroundStyle(Color.soft)
        }
    }

    @ViewBuilder private var status: some View {
        if let failed = session.messages.last(where: { session.isMine($0) && $0.status == .error }) {
            Button("Your note did not send. Try again") { Task { await session.retry(failed) } }
                .font(.serif(18))
                .foregroundStyle(Color.rec)
                .buttonStyle(PressStyle())
                .tapTarget()
                .accessibilityIdentifier("almanac.retry")
                .padding(.top, 14)
        } else if session.hasPending {
            Breathing {
                Text("Your note to \(session.partnerName) is on its way.")
                    .font(.serif(18))
                    .foregroundStyle(Color.soft)
            }
            .accessibilityIdentifier("almanac.pending")
            .padding(.top, 14)
        }
    }

    private func index(_ rows: [Message]) -> some View {
        VStack(spacing: 0) {
            ForEach(Array(rows.enumerated()), id: \.element.id) { i, m in
                let sameDay = i > 0 && Almanac.calendar.isDate(rows[i - 1].date, inSameDayAs: m.date)
                let mine = session.isMine(m)
                Button { open(m.id) } label: {
                    HStack(alignment: .firstTextBaseline, spacing: 0) {
                        Text(sameDay ? "" : "\(Almanac.dayNumber(m.date))")
                            .font(.serif(22))
                            .monospacedDigit()
                            .foregroundStyle(mine ? Color.later : Color.sub)
                            .frame(width: 44, alignment: .leading)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(Almanac.titleEn(m))
                                .font(.serif(19))
                                .foregroundStyle(Color.ink)
                            Text(Almanac.titleEs(m))
                                .font(.serif(15))
                                .foregroundStyle(Color.sub)
                            if mine {
                                Text("You sent this")
                                    .font(.serif(15))
                                    .foregroundStyle(Color.soft)
                            }
                        }
                        .multilineTextAlignment(.leading)
                        Spacer(minLength: 0)
                    }
                    .padding(.top, 10)
                    .padding(.bottom, 9)
                    .contentShape(.rect)
                }
                .buttonStyle(PressStyle())
                .accessibilityIdentifier("almanac.row")
                .overlay(alignment: .bottom) { Hairline() }
            }
        }
        .overlay(alignment: .top) { if !rows.isEmpty { Hairline() } }
    }
}

/// One slow opacity breathe, held still under Reduce Motion.
struct Breathing<Content: View>: View {
    @ViewBuilder var content: Content
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var dim = false

    var body: some View {
        content
            .opacity(dim ? 0.55 : 1)
            .onAppear {
                guard !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 2.4).repeatForever(autoreverses: true)) { dim = true }
            }
    }
}
