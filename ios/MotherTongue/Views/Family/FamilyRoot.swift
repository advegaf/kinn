import SwiftUI

/// The grandkid side: the almanac, an entry opened from it, and the page for writing back.
struct FamilyRoot: View {
    enum Route: Hashable {
        case week
        case entry(UUID)
        case write(UUID)
        case compose
    }

    @Environment(AppSession.self) private var session
    /// Pages opened on top of the week, oldest first. Back drops the last one.
    @State private var history: [Route] = []
    /// True after Back, so an entry shown again does not start its story again.
    @State private var cameBack = false
    @State private var showSettings = false
    #if DEBUG
    @State private var debugApplied = false
    #endif

    var body: some View {
        ZStack {
            switch route {
            case .week:
                AlmanacView(open: { push(.entry($0)) })
                    .kinnTabBar(home: { history = [] }, compose: { push(.compose) }, settings: { showSettings = true })
                    .transition(.fade)
            case .entry(let id):
                if let m = message(id) {
                    EntryView(message: m, autoplay: !cameBack, back: back, writeBack: { push(.write(id)) })
                        .transition(.fade)
                }
            case .write(let id):
                if let m = message(id) {
                    WriteBackView(message: m, back: back, sent: { history = [] })
                        .transition(.fade)
                }
            case .compose:
                WriteBackView(message: nil, back: back, sent: { history = [] })
                    .transition(.fade)
            }
        }
        .animation(.enter, value: route)
        .preferredColorScheme(isEntry ? .dark : .light)
        .sheet(isPresented: $showSettings) { SettingsView() }
        #if DEBUG
        .task(id: session.messages.count) { applyDebugRoute() }
        #endif
    }

    private var route: Route { history.last ?? .week }

    private func back() {
        session.player.stop()
        session.recorder.cancel()
        cameBack = true
        history.popLast()
    }

    private func push(_ next: Route) {
        cameBack = false
        history.append(next)
    }

    private var isEntry: Bool {
        if case .entry = route { true } else { false }
    }

    private func message(_ id: UUID) -> Message? {
        session.messages.first { $0.id == id }
    }

    #if DEBUG
    /// Screenshot aids: `-compose YES`, `-openEntry YES`, `-writingBack YES`, `-fakeRecording YES`, `-openSettings YES`.
    private func applyDebugRoute() {
        guard !debugApplied else { return }
        let d = UserDefaults.standard
        if d.bool(forKey: "compose") {
            debugApplied = true
            history = [.compose]
            return
        }
        guard let latest = session.latestFromPartner else { return }
        debugApplied = true
        if d.bool(forKey: "writingBack") || d.bool(forKey: "fakeRecording") {
            history = [.entry(latest.id), .write(latest.id)]
        } else if d.bool(forKey: "openEntry") {
            history = [.entry(latest.id)]
        }
        if d.bool(forKey: "openSettings") { showSettings = true }
    }
    #endif
}
