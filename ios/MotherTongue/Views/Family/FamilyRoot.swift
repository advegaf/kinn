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
    @State private var route: Route = .week
    @State private var showSettings = false
    #if DEBUG
    @State private var debugApplied = false
    #endif

    var body: some View {
        ZStack {
            switch route {
            case .week:
                AlmanacView(open: { route = .entry($0) })
                    .kinnTabBar(home: { route = .week }, compose: { route = .compose }, settings: { showSettings = true })
                    .transition(.fade)
            case .entry(let id):
                if let m = message(id) {
                    EntryView(message: m, close: { route = .week }, writeBack: { route = .write(id) })
                        .transition(.fade)
                }
            case .write(let id):
                if let m = message(id) {
                    WriteBackView(message: m, close: { route = .week }, sent: { route = .week })
                        .transition(.fade)
                }
            case .compose:
                WriteBackView(message: nil, close: { route = .week }, sent: { route = .week })
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
            route = .compose
            return
        }
        guard let latest = session.latestFromPartner else { return }
        debugApplied = true
        if d.bool(forKey: "writingBack") || d.bool(forKey: "fakeRecording") {
            route = .write(latest.id)
        } else if d.bool(forKey: "openEntry") {
            route = .entry(latest.id)
        }
        if d.bool(forKey: "openSettings") { showSettings = true }
    }
    #endif
}
