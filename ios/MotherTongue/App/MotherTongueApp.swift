import SwiftUI

@main
struct MotherTongueApp: App {
    @State private var session = AppSession()

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
