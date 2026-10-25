import SwiftUI

struct PairView: View {
    @Environment(AppSession.self) private var session
    var onDone: () -> Void

    @State private var openThreads: [OpenThread] = []
    @State private var code = ""
    @State private var busy = false
    @State private var error: String?

    private var isElder: Bool { session.profile?.role == .elder }

    var body: some View {
        Group {
            if isElder { elderPage } else { familyPage }
        }
        .task { await load() }
    }

    // MARK: Family: show the code her Hearth needs

    private var familyPage: some View {
        OnbPage(left: "Kinn", right: "First page") {
            VStack(alignment: .leading, spacing: 0) {
                OnbHeadline(title: "Connect to her Hearth", note: "Enter these on her Hearth.")

                if let thread = session.thread {
                    VStack(alignment: .leading, spacing: 0) {
                        MiniHearth(code: thread.code)
                        CodeSlots(code: thread.code).padding(.top, 26)
                    }
                    .padding(.top, 30)
                    .transition(.fade)
                    .accessibilityElement(children: .ignore)
                    .accessibilityLabel("Family code \(thread.code.map(String.init).joined(separator: " "))")
                } else if error == nil {
                    ProgressView().tint(.ink).padding(.top, 40)
                }

                Text("Once she types them, her Hearth will hold your stories.")
                    .font(.serif(18))
                    .foregroundStyle(Color.soft)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.top, 30)

                if let error { OnbNotice(text: error).padding(.top, 20) }
            }
            .animation(.enter, value: session.thread?.code)
        } footer: {
            slab("Next, your voice", enabled: session.thread != nil) { onDone() }
        }
    }

    // MARK: Elder: type the code from the family phone

    private var elderPage: some View {
        OnbPage(left: "Kinn", right: "Primera p\u{E1}gina") {
            VStack(alignment: .leading, spacing: 0) {
                OnbHeadline(title: "Tu familia", note: "Escribe las letras que ves en su tel\u{E9}fono.")

                CodeEntry(code: $code).padding(.top, 34)

                VStack(spacing: 0) {
                    if !openThreads.isEmpty {
                        Text("O toca tu familia").tinyCaps()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.bottom, 12)
                        Hairline()
                    }
                    ForEach(openThreads) { open in
                        Button { join(open.thread) } label: {
                            VStack(spacing: 0) {
                                HStack(alignment: .firstTextBaseline) {
                                    Text(open.family?.name ?? "Familia")
                                        .font(.serif(26))
                                        .foregroundStyle(Color.ink)
                                    Spacer()
                                    Text(open.thread.code).tinyCaps(size: 12)
                                }
                                .padding(.vertical, 14)
                                Hairline()
                            }
                            .contentShape(.rect)
                        }
                        .buttonStyle(PressStyle())
                    }
                }
                .padding(.top, 36)

                Button { Task { await load() } } label: {
                    Text(openThreads.isEmpty && !busy ? "Nadie esperando todav\u{ED}a. Buscar otra vez" : "Buscar otra vez")
                        .font(.serif(18))
                        .foregroundStyle(Color.soft)
                        .underline(color: .faint)
                        .multilineTextAlignment(.leading)
                }
                .buttonStyle(PressStyle())
                .tapTarget()
                .padding(.top, 8)

                if let error { OnbNotice(text: error).padding(.top, 20) }
            }
        } footer: {
            slab("Unirme", enabled: code.count >= 4) {
                run { try await session.join(code: code) }
            }
        }
    }

    private func slab(_ title: String, enabled: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 10) {
                if busy { ProgressView().tint(.cream) }
                Text(title)
            }
        }
        .buttonStyle(SlabButtonStyle())
        .disabled(!enabled || busy)
        .opacity(!enabled || busy ? 0.45 : 1)
    }

    private func load() async {
        error = nil
        busy = true
        defer { busy = false }
        do {
            if isElder {
                openThreads = try await session.openThreads()
            } else if session.thread == nil {
                try await session.createThread()
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func join(_ thread: ChatThread) {
        run { try await session.join(thread) }
    }

    private func run(_ work: @escaping () async throws -> Void) {
        busy = true
        error = nil
        Task {
            defer { busy = false }
            do {
                try await work()
                Haptics.arrival()
                onDone()
            } catch {
                Haptics.error()
                self.error = error.localizedDescription
            }
        }
    }
}

// MARK: Code parts

/// Six serif characters, each on its own underline.
struct CodeSlots: View {
    var code: String
    var caretAt: Int? = nil
    private let count = 6

    var body: some View {
        let chars = Array(code)
        HStack(spacing: 12) {
            ForEach(0..<count, id: \.self) { i in
                let filled = i < chars.count
                ZStack {
                    if filled {
                        Text(String(chars[i]))
                            .font(.serif(48))
                            .monospacedDigit()
                            .foregroundStyle(Color.ink)
                    } else if caretAt == i {
                        Caret(height: 34)
                    }
                }
                .frame(width: 44, height: 62)
                .background(Color.white.opacity(0.22))
                .overlay(alignment: .bottom) {
                    Rectangle()
                        .fill(filled || caretAt == i ? Color.ink : Color.ink.opacity(0.3))
                        .frame(height: 1.5)
                }
            }
        }
        .accessibilityHidden(true)
    }
}

/// Code slots with a hidden field on top, for typing on the Hearth.
struct CodeEntry: View {
    @Binding var code: String
    @FocusState private var focused: Bool

    var body: some View {
        CodeSlots(code: code, caretAt: focused && code.count < 6 ? code.count : nil)
            .overlay {
                TextField("", text: $code)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                    .keyboardType(.asciiCapable)
                    .textContentType(.oneTimeCode)
                    .foregroundStyle(.clear)
                    .tint(.clear)
                    .focused($focused)
                    .accessibilityLabel("C\u{F3}digo")
            }
            .contentShape(.rect)
            .onTapGesture { focused = true }
            .onChange(of: code) { _, new in
                let clean = String(new.uppercased().filter { $0.isLetter || $0.isNumber }.prefix(6))
                if clean != new { code = clean }
            }
    }
}

/// A small taupe Hearth with the code lit on its night glass.
struct MiniHearth: View {
    var code: String

    var body: some View {
        HStack(spacing: 14) {
            Text(code.map(String.init).joined(separator: " "))
                .font(.serif(28))
                .monospacedDigit()
                .foregroundStyle(Color.cream)
                .lineLimit(1)
                .minimumScaleFactor(0.6)
                .frame(width: 176, height: 50)
                .background(Color.night, in: .rect(cornerRadius: 6))
                .padding(2)
                .background(Color(hex: 0xC4BBAC), in: .rect(cornerRadius: 8))
            Circle()
                .fill(Color(hex: 0xC8BFB1))
                .overlay(
                    Circle().stroke(Color(hex: 0x463A2C, opacity: 0.35), lineWidth: 3)
                        .blur(radius: 2).offset(y: 1.5).mask(Circle())
                )
                .frame(width: 22, height: 22)
        }
        .padding(.leading, 10)
        .frame(width: 236, height: 74, alignment: .leading)
        .background {
            RoundedRectangle(cornerRadius: 22)
                .fill(Color.taupe)
                .overlay(
                    RoundedRectangle(cornerRadius: 22)
                        .fill(LinearGradient(colors: [.white.opacity(0.18), .clear, Color(hex: 0x5A4C3A, opacity: 0.16)],
                                             startPoint: .top, endPoint: .bottom))
                )
                .overlay(RoundedRectangle(cornerRadius: 22).strokeBorder(.white.opacity(0.45), lineWidth: 0.75).blendMode(.overlay))
                .shadow(color: Color(hex: 0x3C3226, opacity: 0.35), radius: 8, y: 8)
        }
        .accessibilityHidden(true)
    }
}
