import SwiftUI

struct OnboardingFlow: View {
    enum Step { case welcome, pair, voice }

    @Environment(AppSession.self) private var session
    @AppStorage(StorageKeys.onboarded) private var onboarded = false
    @AppStorage(StorageKeys.name) private var name = ""
    @AppStorage(StorageKeys.role) private var role: Role = .family
    @AppStorage(StorageKeys.lang) private var lang = "en"
    @AppStorage(StorageKeys.demoMode) private var demoMode = false
    @State private var step: Step = .welcome
    @State private var busy = false
    @State private var error: String?
    /// Kept here so the code typed on the pair page is still there after a step back.
    @State private var code = ""
    /// Display only: the backend learns her language when her Hearth joins.
    @State private var herLang = "es"

    private var isElder: Bool { role == .elder }
    private var trimmedName: String { name.trimmingCharacters(in: .whitespaces) }
    private func languageLabel(_ code: String) -> String { isElder ? endonym(code) : languageName(code) }

    var body: some View {
        ZStack {
            switch step {
            case .welcome: welcome.transition(.fade)
            case .pair:
                PairView(code: $code, onBack: { advance(to: .welcome) }) { joined in joined ? finish() : advance(to: .voice) }
                    .transition(.fade)
            case .voice: VoiceEnrollView(onBack: { advance(to: .pair) }, onDone: finish).transition(.fade)
            }
        }
        .animation(.enter, value: step)
        #if DEBUG
        .task { await jumpForScreenshot() }
        #endif
    }

    #if DEBUG
    /// Debug screenshots only: `-onboardingStep pair|voice` skips ahead, and with `-pairCode XXXXXX`
    /// the family phone joins that thread by code, as typing it on the pair page would.
    private func jumpForScreenshot() async {
        guard let target = UserDefaults.standard.string(forKey: "onboardingStep"), step == .welcome else { return }
        session.configureBackend()
        try? await session.createProfile(name: name.isEmpty ? "Angel" : name, role: role, lang: role == .family ? "en" : lang)
        if let code = UserDefaults.standard.string(forKey: "pairCode"), role == .family {
            do {
                try await session.join(code: code)
                finish()
            } catch {
                self.error = error.localizedDescription
            }
            return
        }
        if target != "voice", role == .family, session.thread == nil { try? await session.createThread() }
        step = target == "voice" ? .voice : .pair
    }
    #endif

    private var headline: String {
        if isElder { return "Tu Hearth" }
        if let partner = session.partner?.name, !partner.isEmpty { return "For Grandma \(partner)" }
        return "For your grandma"
    }

    private var welcome: some View {
        OnbPage {
            VStack(alignment: .leading, spacing: 0) {
                OnbHeadline(title: headline, note: isElder ? "Para ti, de tu familia" : "Who this is for")

                VStack(spacing: 0) {
                    Hairline()
                    DiaryFormRow(key: isElder ? "Nombre" : "From", note: isElder ? "Name" : "Your name") {
                        TextField("", text: $name, prompt: Text(isElder ? "Margaret" : "Angel").foregroundStyle(Color.faint))
                            .textContentType(.givenName)
                            .font(.serif(26))
                            .foregroundStyle(Color.ink)
                            .tint(.ink)
                            .submitLabel(.done)
                    }
                    if !isElder {
                        DiaryFormRow(key: "She speaks", note: "Her language") { LanguageMenu(selection: $herLang, name: languageName) }
                    }
                    if isElder {
                        DiaryFormRow(key: "Hablas", note: "You speak") { LanguageMenu(selection: $lang, name: languageLabel) }
                    } else {
                        DiaryFormRow(key: "You speak", note: "Your language") {
                            Text("English")
                                .font(.serif(26))
                                .foregroundStyle(Color.ink)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }
                .padding(.top, 26)

                Button(isElder ? "This phone is for family" : "This phone is her Hearth") { switchRole() }
                    .font(.serifItalic(18))
                    .foregroundStyle(Color.soft)
                    .underline(color: .faint)
                    .buttonStyle(PressStyle())
                    .padding(.top, 22)

                Toggle(isOn: $demoMode) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Demo mode").font(.serif(19)).foregroundStyle(Color.ink)
                        Text("Canned data, no network").font(.serifItalic(15)).foregroundStyle(Color.sub)
                    }
                }
                .tint(.ink)
                .padding(.top, 34)

                if !AppConfig.isConfigured && !demoMode {
                    OnbNotice(text: "No backend configured. Add ios/Config/Secrets.xcconfig, or use demo mode.")
                        .padding(.top, 20)
                }
                if let error { OnbNotice(text: error).padding(.top, 20) }
            }
        } footer: {
            Button(action: begin) {
                HStack(spacing: 10) {
                    if busy { ProgressView().tint(.cream) }
                    Text(isElder ? "Continuar" : "Connect to her Hearth")
                }
            }
            .buttonStyle(SlabButtonStyle())
            .disabled(busy || trimmedName.isEmpty)
            .opacity(busy || trimmedName.isEmpty ? 0.45 : 1)
        }
    }

    private func switchRole() {
        Haptics.tap()
        withAnimation(.enter) {
            if isElder { role = .family; lang = "en" } else { role = .elder; lang = "es" }
        }
    }

    private func begin() {
        busy = true
        error = nil
        Task {
            defer { busy = false }
            session.configureBackend()
            do {
                try await session.createProfile(name: trimmedName, role: role, lang: role == .family ? "en" : lang)
                advance(to: .pair)
            } catch {
                self.error = error.localizedDescription
            }
        }
    }

    private func advance(to next: Step) {
        withAnimation(.enter) { step = next }
    }

    private func finish() {
        onboarded = true
    }
}

// MARK: Diary page parts shared by the onboarding pages and settings

/// A diary page: content, and one action held at the foot.
struct OnbPage<Content: View, Footer: View>: View {
    var back: BackButton? = nil
    @ViewBuilder var content: Content
    @ViewBuilder var footer: Footer

    var body: some View {
        GeometryReader { geo in
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if let back { back.padding(.bottom, 22) }
                    content
                    Spacer(minLength: 32)
                    footer
                }
                .padding(.horizontal, 30)
                .padding(.top, 24)
                .padding(.bottom, 24)
                .frame(maxWidth: 560, minHeight: geo.size.height, alignment: .top)
                .frame(maxWidth: .infinity)
            }
            .scrollIndicators(.hidden)
            .scrollDismissesKeyboard(.interactively)
            .screenshotAnchor()
        }
        .background { PaperCanvas() }
        .backSwipe(back?.action)
    }
}

struct OnbHeadline: View {
    var title: String
    var note: String
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.serif(52))
                .tracking(-1.3)
                .foregroundStyle(Color.ink)
                .lineLimit(2)
                .minimumScaleFactor(0.7)
                .fixedSize(horizontal: false, vertical: true)
            Text(note)
                .font(.serifItalic(19))
                .foregroundStyle(Color.sub)
        }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isHeader)
    }
}

/// One ruled row of the form: a serif key with its English gloss, then the value.
struct DiaryFormRow<Value: View>: View {
    var key: String
    var note: String
    @ViewBuilder var value: Value

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(key).font(.serif(17)).foregroundStyle(Color.soft)
                    Text(note).font(.serifItalic(15)).foregroundStyle(Color(hex: 0x9C968D))
                }
                .frame(width: 96, alignment: .leading)
                value.frame(maxWidth: .infinity, alignment: .leading)
            }
            .padding(.top, 13)
            .padding(.bottom, 11)
            Hairline()
        }
    }
}

/// The language, written as a word. Tapping it opens the choices.
struct LanguageMenu: View {
    @Binding var selection: String
    /// How each language is written: its endonym on the Hearth, English names on the family phone.
    var name: (String) -> String = endonym
    private let options = ["es", "en"]

    var body: some View {
        Menu {
            Picker("Language", selection: $selection) {
                ForEach(options, id: \.self) { Text(name($0)).tag($0) }
            }
        } label: {
            Text(name(selection))
                .font(.serif(26))
                .foregroundStyle(Color.ink)
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(.rect)
        }
        .menuStyle(.button)
        .buttonStyle(.plain)
        .accessibilityValue(languageName(selection))
    }
}

struct OnbNotice: View {
    var text: String
    var body: some View {
        Text(text)
            .font(.serifItalic(17))
            .foregroundStyle(Color.ribbon)
            .fixedSize(horizontal: false, vertical: true)
            .transition(.fade)
    }
}
