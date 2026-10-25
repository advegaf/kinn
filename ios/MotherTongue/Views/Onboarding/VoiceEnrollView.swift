import SwiftUI

struct VoiceEnrollView: View {
    @Environment(AppSession.self) private var session
    var onDone: () -> Void

    @State private var phase: Phase = .ready
    @State private var error: String?
    @ScaledMetric(relativeTo: .body) private var scriptSize: CGFloat = 22
    private let target: TimeInterval = 30
    private let scriptSpacing: CGFloat = 9

    enum Phase { case ready, recording, uploading, done }

    /// The phone belongs to the grandchild, who reads English. Only the elder path is Spanish,
    /// so key off the role, not the stored language (a stale "es" pick used to leak in here).
    private var es: Bool { session.role == .elder }

    private var script: String {
        es
        ? "Hola, mi amor. Hoy amaneció bonito y me acordé de ti. En la mañana hice café de olla y abrí las ventanas para que entrara el aire. Me gusta escuchar a los pájaros mientras riego las plantas. Cuando vengas, te voy a contar cómo era la casa de mis papás, con su patio lleno de flores y la cocina siempre oliendo a tortillas. Te quiero mucho y te pienso siempre."
        : "Hi Grandma, it is me. Today was a long day, but a good one. I walked to class early and the air already felt like fall. I keep thinking about your kitchen, the smell of coffee and fresh tortillas, and the radio always playing in the background. When I come home, I want you to teach me the recipes and tell me the stories again, slowly, so I remember them. I love you and I miss you."
    }

    var body: some View {
        OnbPage(left: "Kinn", right: es ? "Segunda p\u{E1}gina" : "Second page") {
            VStack(alignment: .leading, spacing: 0) {
                OnbHeadline(title: es ? "Tu voz" : "Your voice",
                            note: es ? "Lee esto en voz alta, con calma. Unos 30 segundos." : "Read this aloud, slowly. About thirty seconds.")

                ruledScript.padding(.top, 28)

                Text(es ? "Tu voz solo se usa para decir tus propios mensajes a tu familia." : "Your voice is only used to speak your own messages to your family.")
                    .font(.serif(17))
                    .foregroundStyle(Color.soft)
                    .fixedSize(horizontal: false, vertical: true)
                    .padding(.leading, 16)
                    .overlay(alignment: .leading) { Rectangle().fill(Color.madder).frame(width: 1) }
                    .padding(.top, 22)

                if let error { OnbNotice(text: error).padding(.top, 18) }
            }
        } footer: {
            VStack(alignment: .leading, spacing: 22) {
                if phase == .done {
                    Button(es ? "Continuar" : "Continue") { onDone() }
                        .buttonStyle(SlabButtonStyle())
                        .transition(.fade)
                } else {
                    recordControl
                    Button(es ? "Saltar por ahora" : "Skip for now") {
                        session.recorder.cancel()
                        onDone()
                    }
                    .font(.serif(17))
                    .foregroundStyle(Color.sub)
                    .underline(color: .faint)
                    .buttonStyle(PressStyle())
                    .tapTarget()
                }
            }
            .animation(.enter, value: phase)
        }
    }

    /// The script on ruled lines, one hairline under each line of type.
    private var ruledScript: some View {
        let ui = UIFont(name: "InstrumentSerif-Regular", size: scriptSize) ?? .systemFont(ofSize: scriptSize)
        let pitch = ui.lineHeight + scriptSpacing
        let underBaseline = ui.ascender + max(4, -ui.descender * 0.6)
        return Text(script)
            .font(.custom("InstrumentSerif-Regular", fixedSize: scriptSize))
            .lineSpacing(scriptSpacing)
            .foregroundStyle(Color.ink)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.top, 10)
            .background(alignment: .top) {
                GeometryReader { geo in
                    let lines = Int(((geo.size.height - 10) / pitch).rounded())
                    ZStack(alignment: .top) {
                        Hairline()
                        ForEach(0..<max(lines, 0), id: \.self) { i in
                            Hairline().offset(y: 10 + CGFloat(i) * pitch + underBaseline)
                        }
                    }
                }
            }
    }

    private var recordControl: some View {
        let recorder = session.recorder
        let live = phase == .recording
        return HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 6) {
                if live {
                    HStack(spacing: 7) {
                        Circle().fill(Color.rec).frame(width: 7, height: 7)
                        Text("Rec").tinyCaps(.rec, size: 11, medium: true, tracking: 0.12)
                    }
                    .transition(.fade)
                    Text(counter(recorder.elapsed))
                        .font(.sansLight(44))
                        .monospacedDigit()
                        .foregroundStyle(Color.ink)
                        .contentTransition(.identity)
                }
                Text(hint)
                    .font(.serif(18))
                    .foregroundStyle(Color.soft)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 16)
            Button(action: tapped) {
                ZStack {
                    RecordDisc(live: live)
                    if phase == .uploading { ProgressView().tint(.cream) }
                }
            }
            .buttonStyle(PressStyle())
            .disabled(phase == .uploading)
            .accessibilityLabel(live ? (es ? "Terminar" : "Stop recording") : (es ? "Grabar" : "Start recording"))
            .accessibilityValue(hint)
        }
        .animation(.enter, value: live)
    }

    private func counter(_ t: TimeInterval) -> String {
        let s = max(0, Int(t.rounded(.down)))
        return String(format: "%02d:%02d", s / 60, s % 60)
    }

    private var hint: String {
        switch phase {
        case .ready: es ? "Toca el disco y lee" : "Tap the disc and read"
        case .recording:
            session.recorder.elapsed >= 20 ? (es ? "Toca para terminar" : "Tap to finish") : (es ? "Sigue leyendo, hasta 0:30" : "Keep reading, up to 0:30")
        case .uploading: es ? "Guardando tu voz" : "Saving your voice"
        case .done: es ? "Listo" : "All set"
        }
    }

    private func tapped() {
        switch phase {
        case .ready:
            error = nil
            Task {
                do {
                    try await session.recorder.start(allowSimulated: session.isDemo)
                    Haptics.recordStart()
                    withAnimation(.enter) { phase = .recording }
                } catch {
                    self.error = error.localizedDescription
                }
            }
        case .recording:
            Haptics.recordStop()
            let result = session.recorder.stop()
            if result.duration < 8 {
                error = es ? "Un poquito más largo, por favor." : "A bit longer, please. Aim for about 30 seconds."
                phase = .ready
                return
            }
            withAnimation(.enter) { phase = .uploading }
            Task {
                do {
                    try await session.enrollVoice(sample: result.url)
                    Haptics.arrival()
                    withAnimation(.enter) { phase = .done }
                } catch {
                    self.error = es
                        ? "No pudimos guardar tu voz ahora. Puedes seguir y probar otra vez después."
                        : "We could not save your voice right now. Skip for now and try again later in Settings."
                    withAnimation(.enter) { phase = .ready }
                }
            }
        default: break
        }
    }
}
