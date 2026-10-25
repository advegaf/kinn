import SwiftUI

@main
struct MotherTongueApp: App {
    @State private var session: AppSession

    init() {
        #if DEBUG
        // UI tests: `-uiTestReset` starts each launch from a fresh install.
        if CommandLine.arguments.contains("-uiTestReset"), let id = Bundle.main.bundleIdentifier {
            UserDefaults.standard.removePersistentDomain(forName: id)
        }
        #endif
        _session = State(initialValue: AppSession())
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(session)
        }
    }
}

struct RootView: View {
    @Environment(AppSession.self) private var session
    @AppStorage(StorageKeys.onboarded) private var onboarded = false
    @AppStorage(StorageKeys.role) private var role: Role = .family
    @AppStorage(StorageKeys.demoMode) private var demoMode = false

    var body: some View {
        ZStack {
            PaperCanvas()
            if !onboarded {
                OnboardingFlow()
                    .preferredColorScheme(.light)
                    .transition(.opacity)
            } else if role == .elder {
                HearthView()
                    .transition(.opacity)
            } else {
                FamilyRoot()
                    .transition(.opacity)
            }
        }
        .animation(.gentle, value: onboarded)
        .tint(.ink)
        .task(id: "\(onboarded)-\(demoMode)") {
            if onboarded { await session.start() }
        }
        .onChange(of: demoMode) {
            session.configureBackend()
        }
    }
}
