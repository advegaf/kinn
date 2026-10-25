import SwiftUI

/// The grandkid side: the almanac, and the pages opened on top of it.
struct FamilyRoot: View {
    enum Route: Hashable {
        case archive
        case entry(UUID)
        case write(UUID)
        case compose
        case settings
        case voice
    }

    @Environment(AppSession.self) private var session
    /// Pages opened on top of the week, oldest first. Back drops the last one.
    @State private var history: [Route] = []
    #if DEBUG
    @State private var debugApplied = false
    #endif

    var body: some View {
        PageStack(path: history, pop: dropTop) {
            AlmanacView(open: { push(.entry($0)) })
                .kinnTabBar(home: { history = [] }, archive: { push(.archive) }, compose: { push(.compose) }, settings: { push(.settings) })
                .background { PaperCanvas() }
        } page: { route in
            page(route)
        }
        .preferredColorScheme(isEntry ? .dark : .light)
        #if DEBUG
        .task(id: session.messages.count) { applyDebugRoute() }
        #endif
    }

    @ViewBuilder private func page(_ route: Route) -> some View {
        switch route {
        case .archive:
            ArchiveView(open: { push(.entry($0)) }, back: back, compose: { push(.compose) })
        case .entry(let id):
            if let m = message(id) {
                EntryView(message: m, back: back, writeBack: { push(.write(id)) })
            }
        case .write(let id):
            if let m = message(id) {
                WriteBackView(message: m, back: back, sent: home)
            }
        case .compose:
            WriteBackView(message: nil, back: back, sent: home)
        case .settings:
            SettingsView(back: BackButton(action: back), recordVoice: { push(.voice) })
        case .voice:
            VoiceEnrollView(onBack: back, onDone: back)
        }
    }

    private func push(_ next: Route) {
        guard history.last != next else { return }
        withAnimation(.push) { history.append(next) }
    }

    private func back() {
        withAnimation(.pop) { dropTop() }
    }

    private func dropTop() {
        session.player.stop()
        session.recorder.cancel()
        history.removeLast()
    }

    private func home() {
        withAnimation(.pop) { history = [] }
    }

    private var isEntry: Bool {
        if case .entry = history.last { true } else { false }
    }

    private func message(_ id: UUID) -> Message? {
        session.messages.first { $0.id == id }
    }

    #if DEBUG
    /// Screenshot aids: `-openArchive YES`, `-compose YES`, `-openEntry YES`, `-writingBack YES`, `-fakeRecording YES`, `-openSettings YES`.
    private func applyDebugRoute() {
        guard !debugApplied else { return }
        let d = UserDefaults.standard
        if d.bool(forKey: "openArchive") {
            debugApplied = true
            history = [.archive]
            return
        }
        if d.bool(forKey: "compose") {
            debugApplied = true
            history = [.compose]
            return
        }
        if d.bool(forKey: "openSettings") {
            debugApplied = true
            history = [.settings]
            return
        }
        guard let latest = session.latestFromPartner else { return }
        debugApplied = true
        if d.bool(forKey: "writingBack") || d.bool(forKey: "fakeRecording") {
            history = [.entry(latest.id), .write(latest.id)]
        } else if d.bool(forKey: "openEntry") {
            history = [.entry(latest.id)]
        }
    }
    #endif
}
