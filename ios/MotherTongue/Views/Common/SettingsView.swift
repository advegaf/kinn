import SwiftUI

struct SettingsView: View {
    var back: BackButton
    var recordVoice: () -> Void
    @Environment(AppSession.self) private var session
    @Environment(\.dismiss) private var dismiss
    @AppStorage(StorageKeys.onboarded) private var onboarded = false
    @AppStorage(StorageKeys.demoMode) private var demoMode = false
    @AppStorage(StorageKeys.shutterRemote) private var shutterRemote = false
    @AppStorage(StorageKeys.role) private var role: Role = .family

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                back.accessibilityIdentifier("settings.done")
                OnbHeadline(title: "Settings")
                    .padding(.top, 22)

                Disclosure(title: "Profile", id: "settings.profile") {
                    row("Name", session.profile?.name ?? "")
                    row("Role", role == .elder ? "Hearth" : "Family")
                    if let code = session.thread?.code {
                        row("Family code", code.map(String.init).joined(separator: " "))
                    }
                    row("Voice", session.profile?.voiceId == nil ? "Not recorded" : "Cloned")
                    link("Record my voice again", action: recordVoice)
                }
                .padding(.top, 34)

                if role == .elder {
                    section("Hearth") {
                        toggle("Shutter remote as button", isOn: $shutterRemote)
                        note("Pair a Bluetooth camera remote. Its press (volume up) works like tapping the big button.")
                    }
                }

                section("Demo") {
                    toggle("Demo mode", isOn: $demoMode)
                        .accessibilityIdentifier("settings.demoMode")
                }

                Button("Start over") {
                    session.reset()
                    onboarded = false
                    dismiss()
                }
                .font(.serif(21))
                .foregroundStyle(Color.ribbon)
                .buttonStyle(PressStyle())
                .accessibilityIdentifier("settings.startOver")
                .padding(.top, 40)
            }
            .padding(.horizontal, 30)
            .padding(.top, 24)
            .padding(.bottom, 40)
            .frame(maxWidth: 560)
            .frame(maxWidth: .infinity)
        }
        .scrollIndicators(.hidden)
        .background { PaperCanvas() }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionTitle(text: title)
                .padding(.bottom, 10)
                .accessibilityAddTraits(.isHeader)
            Hairline()
            content()
        }
        .padding(.top, 34)
    }

    private func row(_ label: String, _ value: String) -> some View {
        VStack(spacing: 0) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(label).font(.serif(17)).foregroundStyle(Color.soft)
                    .frame(width: 110, alignment: .leading)
                Text(value).font(.serif(22)).foregroundStyle(Color.ink)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.vertical, 12)
            Hairline()
        }
        .accessibilityElement(children: .combine)
    }

    private func toggle(_ label: String, isOn: Binding<Bool>) -> some View {
        VStack(spacing: 0) {
            Toggle(isOn: isOn) {
                Text(label).font(.serif(19)).foregroundStyle(Color.ink)
            }
            .toggleStyle(TickToggleStyle())
            .padding(.vertical, 4)
            Hairline()
        }
    }

    private func link(_ label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(label)
                .font(.serif(18))
                .foregroundStyle(Color.soft)
                .underline(color: .faint)
                .tapTarget()
        }
        .buttonStyle(PressStyle())
        .padding(.top, 4)
    }

    private func note(_ text: String) -> some View {
        Text(text)
            .font(.serif(16))
            .foregroundStyle(Color.sub)
            .fixedSize(horizontal: false, vertical: true)
            .padding(.top, 10)
    }
}
