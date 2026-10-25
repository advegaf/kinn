import SwiftUI

struct PairView: View {
    @Environment(AppSession.self) private var session
    @Binding var code: String
    var onBack: () -> Void
    /// `joinedByCode` is true when the family phone joined an existing thread, so there is no voice step.
    var onDone: (_ joinedByCode: Bool) -> Void

    @State private var openThreads: [OpenThread] = []
    @State private var busy = false
    @State private var error: String?
    /// Cancelled when the page goes away, so a late reply cannot move the flow after Back.
    @State private var pending: Task<Void, Never>?

    private var isElder: Bool { session.profile?.role == .elder }

    var body: some View {
        Group {
            if isElder { elderPage } else { familyPage }
        }
        .task { if isElder { await load() } }
        .onDisappear { pending?.cancel() }
    }

    // MARK: Family: type the code her Hearth shows

    private var familyPage: some View {
        OnbPage(left: "Kinn", right: "First page", back: BackButton(action: onBack)) {
            VStack(alignment: .leading, spacing: 0) {
                OnbHeadline(title: "Type the code on her Hearth", note: "Six letters and numbers on her clock.")

                CodeEntry(code: $code, label: "Family code").padding(.top, 34)

                if code.count < 6 {
                    Text("Connect works once all six are in.")
                        .font(.serif(17))
                        .foregroundStyle(Color.soft)
                        .padding(.top, 16)
                        .transition(.fade)
                }

                if let error { OnbNotice(text: error).padding(.top, 20) }
            }
            .animation(.enter, value: code.count < 6)
        } footer: {
            VStack(spacing: 14) {
                slab("Connect", enabled: code.count == 6) {
                    run(joinedByCode: true) { try await session.join(code: code) }
                }
                Button("Continue without pairing") {
                    run { if session.thread == nil { try await session.createThread() } }
                }
                .font(.serif(17))
                .foregroundStyle(Color.soft)
                .frame(minHeight: 44)
                .buttonStyle(PressStyle())
                .disabled(busy)
            }
        }
    }

    // MARK: Elder: type the code from the family phone

    private var elderPage: some View {
        OnbPage(left: "Kinn", right: "Primera p\u{E1}gina", back: BackButton(title: "Atr\u{E1}s", action: onBack)) {
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
                        .font(.serifItalic(18))
                        .foregroundStyle(Color.soft)
                        .underline(color: .faint)
                        .multilineTextAlignment(.leading)
                }
                .buttonStyle(PressStyle())
                .padding(.top, 18)

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
            openThreads = try await session.openThreads()
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func join(_ thread: ChatThread) {
        run { try await session.join(thread) }
    }

    private func run(joinedByCode: Bool = false, _ work: @escaping () async throws -> Void) {
        busy = true
        error = nil
        pending = Task {
            defer { busy = false }
            do {
                try await work()
                guard !Task.isCancelled else { return }
                Haptics.arrival()
                onDone(joinedByCode)
            } catch {
                guard !Task.isCancelled else { return }
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

/// Code slots with a hidden field on top.
struct CodeEntry: View {
    @Binding var code: String
    var label = "C\u{F3}digo"
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
                    .accessibilityLabel(label)
            }
            .contentShape(.rect)
            .onTapGesture { focused = true }
            .onChange(of: code) { _, new in
                let clean = String(new.uppercased().filter { $0.isLetter || $0.isNumber }.prefix(6))
                if clean != new { code = clean }
            }
    }
}
