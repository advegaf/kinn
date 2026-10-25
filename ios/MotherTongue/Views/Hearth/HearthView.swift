import SwiftUI

struct HearthView: View {
    @Environment(AppSession.self) private var session
    @AppStorage(StorageKeys.shutterRemote) private var shutterRemote = false

    @State private var pressActive = false
    @State private var pressStart: Date?
    @State private var startedThisPress = false
    @State private var sending = false
    @State private var justSent = false
    @State private var showSettings = false
    @State private var glow = false
    @State private var errorText: String?

    private let playKeyPrefix = "hearth-"

    enum Mode: Equatable { case idle, recording, sending, sent, listen, playing }

    private var mode: Mode {
        if session.recorder.isRecording { return .recording }
        if session.player.isPlaying, session.player.currentKey?.hasPrefix(playKeyPrefix) == true { return .playing }
        if sending || session.hasPending { return .sending }
        if !session.unheard.isEmpty { return .listen }
        if justSent { return .sent }
        return .idle
    }

    var body: some View {
        GeometryReader { geo in
            let side = min(geo.size.width, geo.size.height)
            let buttonSize = min(side * 0.62, 460)
            ZStack {
                background
                VStack(spacing: 0) {
                    header
                        .padding(.top, 28)
                    Spacer(minLength: 16)
                    bigButton(size: buttonSize)
                    Spacer(minLength: 16)
                    footer
                        .padding(.bottom, 36)
                }
                .padding(.horizontal, 28)
                .frame(maxWidth: .infinity)
            }
        }
        .ignoresSafeArea()
        .persistentSystemOverlays(.hidden)
        .statusBarHidden(true)
        .preferredColorScheme(.dark)
        .onAppear { UIApplication.shared.isIdleTimerDisabled = true }
        .onDisappear { UIApplication.shared.isIdleTimerDisabled = false }
        .onChange(of: session.arrivals) {
            withAnimation(.gentle) { justSent = false }
        }
        .onChange(of: mode == .listen, initial: true) { _, listening in
            glow = listening
        }
        .sheet(isPresented: $showSettings) { SettingsView() }
        .background {
            if shutterRemote {
                VolumeButtonTrigger { pressDown(); pressUp(forceTap: true) }
            }
        }
    }

    @ViewBuilder
    private var background: some View {
        ZStack {
            LinearGradient(colors: [Color(UIColor(hex: 0x3A1D14)), Color(UIColor(hex: 0x7A3622)), Color(UIColor(hex: 0xB9643A))],
                           startPoint: .top, endPoint: .bottom)
            if let path = session.latestStoryImage {
                KenBurns { StoryImage(path: path) }
                    .opacity(0.85)
                    .transition(.opacity)
                LinearGradient(colors: [.black.opacity(0.45), .black.opacity(0.15), .black.opacity(0.55)],
                               startPoint: .top, endPoint: .bottom)
            }
            RadialGradient(colors: [Color.ember.opacity(glow ? 0.55 : 0), .clear],
                           center: .center, startRadius: 40, endRadius: 520)
                .scaleEffect(glow ? 1.15 : 0.9)
                .animation(glow ? .easeInOut(duration: 2.4).repeatForever(autoreverses: true) : .easeOut(duration: 0.6), value: glow)
            GrainOverlay(opacity: 0.12)
        }
        .ignoresSafeArea()
    }

    private var header: some View {
        VStack(spacing: 6) {
            Text(greeting)
                .font(.display(40, weight: .semibold))
                .foregroundStyle(Color(UIColor(hex: 0xFBEEDD)))
                .multilineTextAlignment(.center)
            if let title = session.messages.last(where: { $0.story?.title != nil })?.story?.title {
                Text(title)
                    .font(.display(22, weight: .regular).italic())
                    .foregroundStyle(Color(UIColor(hex: 0xFBEEDD)).opacity(0.75))
            }
        }
        .shadow(color: .black.opacity(0.35), radius: 10, y: 2)
    }

    private var greeting: String {
        let hour = Calendar.current.component(.hour, from: .now)
        let part = hour < 12 ? "Buenos días" : (hour < 19 ? "Buenas tardes" : "Buenas noches")
        let name = session.profile?.name ?? ""
        return name.isEmpty ? part : "\(part), \(name)"
    }

    private func bigButton(size: CGFloat) -> some View {
        let m = mode
        return ZStack {
            if m == .recording {
                ForEach(0..<3, id: \.self) { i in
                    Circle()
                        .stroke(Color(UIColor(hex: 0xFBEEDD)).opacity(0.25 - Double(i) * 0.07), lineWidth: 2)
                        .scaleEffect(1.04 + CGFloat(session.recorder.level) * (0.18 + CGFloat(i) * 0.12))
                        .animation(.easeOut(duration: 0.12), value: session.recorder.level)
                }
            }
            if m == .listen {
                Circle()
                    .fill(Color.ember.opacity(0.45))
                    .blur(radius: 40)
                    .scaleEffect(glow ? 1.25 : 1.0)
                    .animation(.easeInOut(duration: 1.8).repeatForever(autoreverses: true), value: glow)
            }
            Circle()
                .fill(fill(for: m))
                .shadow(color: .black.opacity(0.35), radius: 30, y: 14)
                .overlay(Circle().stroke(Color.white.opacity(0.25), lineWidth: 1.5))
                .scaleEffect(pressActive ? 0.95 : 1)
            VStack(spacing: 14) {
                icon(for: m)
                    .font(.system(size: size * 0.16, weight: .semibold))
                    .contentTransition(.symbolEffect(.replace))
                Text(label(for: m))
                    .font(.display(size * 0.13, weight: .bold))
                    .contentTransition(.opacity)
            }
            .foregroundStyle(foreground(for: m))
        }
        .frame(width: size, height: size)
        .contentShape(Circle())
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in if !pressActive { pressDown() } }
                .onEnded { _ in pressUp() }
        )
        .animation(.gentle, value: m)
        .animation(.spring(response: 0.25, dampingFraction: 0.7), value: pressActive)
        .accessibilityElement()
        .accessibilityLabel(label(for: m))
        .accessibilityAddTraits(.isButton)
        .accessibilityAction { pressDown(); pressUp(forceTap: true) }
    }

    private var footer: some View {
        ZStack {
            VStack(spacing: 8) {
                Text(subtitle)
                    .font(.system(size: 28, weight: .medium))
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Color(UIColor(hex: 0xFBEEDD)).opacity(0.92))
                    .contentTransition(.opacity)
                    .animation(.gentle, value: subtitle)
                if mode == .recording {
                    Text(formatDuration(session.recorder.elapsed))
                        .font(.system(size: 30, weight: .semibold, design: .rounded).monospacedDigit())
                        .foregroundStyle(Color(UIColor(hex: 0xFBEEDD)))
                        .contentTransition(.numericText())
                }
                if mode == .idle, session.latestFromPartner != nil {
                    Button("Escuchar otra vez") { replayLast() }
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundStyle(Color(UIColor(hex: 0xFBEEDD)))
                        .padding(.horizontal, 22)
                        .padding(.vertical, 12)
                        .background(.white.opacity(0.14), in: .capsule)
                        .padding(.top, 6)
                }
            }
            .frame(maxWidth: .infinity)
            HStack {
                Spacer()
                Image(systemName: "gearshape")
                    .font(.title3)
                    .foregroundStyle(.white.opacity(0.3))
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
                    .onLongPressGesture(minimumDuration: 1) { showSettings = true }
                    .accessibilityLabel("Ajustes, mantén presionado")
            }
            .frame(maxHeight: .infinity, alignment: .bottom)
        }
        .frame(height: 150)
    }

    private var subtitle: String {
        if let errorText { return errorText }
        switch mode {
        case .idle: return "Toca para hablar con \(session.partnerName)"
        case .recording: return "Toca otra vez para enviar"
        case .sending: return "Traduciendo para \(session.partnerName)..."
        case .sent: return "Enviado. \(session.partnerName) lo va a escuchar en inglés, con tu voz."
        case .listen: return "Mensaje nuevo de \(session.partnerName)"
        case .playing: return "Toca para parar"
        }
    }

    private func label(for m: Mode) -> String {
        switch m {
        case .idle, .sent: "Hablar"
        case .recording: "Enviar"
        case .sending: "Enviando"
        case .listen: "Escuchar"
        case .playing: "Escuchando"
        }
    }

    private func icon(for m: Mode) -> Image {
        switch m {
        case .idle: Image(systemName: "mic.fill")
        case .sent: Image(systemName: "checkmark")
        case .recording: Image(systemName: "paperplane.fill")
        case .sending: Image(systemName: "ellipsis")
        case .listen: Image(systemName: "ear.fill")
        case .playing: Image(systemName: "speaker.wave.3.fill")
        }
    }

    private func fill(for m: Mode) -> AnyShapeStyle {
        switch m {
        case .idle, .sent:
            AnyShapeStyle(LinearGradient(colors: [Color(UIColor(hex: 0xFFF6EA)), Color(UIColor(hex: 0xF1DEC6))], startPoint: .top, endPoint: .bottom))
        case .recording:
            AnyShapeStyle(LinearGradient(colors: [Color(UIColor(hex: 0xD06A45)), Color(UIColor(hex: 0xA94A2E))], startPoint: .top, endPoint: .bottom))
        case .sending:
            AnyShapeStyle(Color.white.opacity(0.18))
        case .listen:
            AnyShapeStyle(LinearGradient(colors: [Color(UIColor(hex: 0xF7CF8A)), Color(UIColor(hex: 0xE3A25B))], startPoint: .top, endPoint: .bottom))
        case .playing:
            AnyShapeStyle(LinearGradient(colors: [Color(UIColor(hex: 0x76834A)), Color(UIColor(hex: 0x4F5A2E))], startPoint: .top, endPoint: .bottom))
        }
    }

    private func foreground(for m: Mode) -> Color {
        switch m {
        case .idle, .sent: Color(UIColor(hex: 0xA94A2E))
        case .listen: Color(UIColor(hex: 0x4A2418))
        default: Color(UIColor(hex: 0xFFF6EA))
        }
    }

    private func pressDown() {
        pressActive = true
        pressStart = .now
        startedThisPress = false
        errorText = nil
        if mode == .idle || mode == .sent {
            startedThisPress = true
            justSent = false
            Task {
                do {
                    try await session.recorder.start(allowSimulated: session.isDemo)
                    Haptics.recordStart()
                } catch {
                    Haptics.error()
                    errorText = "No puedo usar el micrófono. Pide ayuda para activarlo."
                }
            }
        }
    }

    private func pressUp(forceTap: Bool = false) {
        pressActive = false
        let held = pressStart.map { Date.now.timeIntervalSince($0) } ?? 0
        pressStart = nil
        switch mode {
        case .recording:
            if startedThisPress && (held < 0.6 || forceTap) { return }
            finishRecording()
        case .listen:
            playNext()
        case .playing:
            session.player.stop()
        default:
            break
        }
    }

    private func finishRecording() {
        Haptics.recordStop()
        let result = session.recorder.stop()
        guard result.duration >= 1 else {
            if let url = result.url { try? FileManager.default.removeItem(at: url) }
            return
        }
        sending = true
        Task {
            await session.send(recording: result.url)
            sending = false
            if let mine = session.messages.last(where: { session.isMine($0) }), mine.status == .error {
                errorText = "No se pudo enviar. Intenta otra vez."
                Haptics.error()
            } else {
                withAnimation(.gentle) { justSent = true }
            }
        }
    }

    private func playNext() {
        guard let message = session.unheard.first, let source = session.translatedSource(message) else { return }
        Haptics.tap()
        session.player.onFinish = { _ in }
        session.player.play(source, key: playKeyPrefix + message.id.uuidString)
        session.markHeard(message.id)
    }

    private func replayLast() {
        guard let message = session.latestFromPartner, let source = session.translatedSource(message) else { return }
        session.player.play(source, key: playKeyPrefix + message.id.uuidString)
    }
}
