import SwiftUI

/// 03 writing back: her line quoted when replying, three prompts in the margin, and a disc to hold while you talk.
struct WriteBackView: View {
    var message: Message?
    var close: () -> Void
    var sent: () -> Void

    @Environment(AppSession.self) private var session
    @State private var selected = 0
    @State private var pressing = false
    @State private var note: String?

    private var recorder: AudioRecorder { session.recorder }
    private var prompts: [String] {
        let asked = Array((message?.askAbout ?? []).prefix(3))
        return asked.isEmpty ? ["Tell her about your day", "Tell her what you ate", "Tell her what made you laugh"] : asked
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            head
            if let message {
                Text(Almanac.quote(message))
                    .font(.serifItalic(22))
                    .foregroundStyle(Color.soft)
                    .lineSpacing(5)
                    .padding(.top, 26)
            }
            if !prompts.isEmpty {
                margin.padding(.top, 26)
            }
            draft
                .padding(.top, 40)
            Spacer(minLength: 20)
            controls
        }
        .padding(.horizontal, 30)
        .padding(.top, 16)
        .padding(.bottom, 12)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .onDisappear { if recorder.isRecording { recorder.cancel() } }
        #if DEBUG
        .task {
            if UserDefaults.standard.bool(forKey: "fakeRecording") {
                selected = min(1, max(0, prompts.count - 1))
                recorder.startFake()
            }
        }
        #endif
    }

    private var head: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(message == nil ? "A new note to \(session.partnerName)" : "To \(session.partnerName)")
                .font(.serif(24, relativeTo: .title2))
                .foregroundStyle(Color.ink)
            Spacer()
            Button("Close") {
                if recorder.isRecording { recorder.cancel() }
                close()
            }
            .tinyCaps()
            .buttonStyle(PressStyle())
            .frame(minWidth: 44, minHeight: 44, alignment: .trailing)
            .contentShape(.rect)
        }
    }

    private var margin: some View {
        VStack(spacing: 0) {
            ForEach(Array(prompts.enumerated()), id: \.offset) { i, prompt in
                let on = i == selected
                Button {
                    Haptics.tap()
                    selected = i
                } label: {
                    HStack(alignment: .firstTextBaseline, spacing: 0) {
                        Text(Almanac.roman(i))
                            .font(.serif(22))
                            .foregroundStyle(on ? Color.ink : Color.fog)
                            .frame(width: 44, alignment: .leading)
                        Text(prompt)
                            .font(.serif(19))
                            .foregroundStyle(on ? Color.ink : Color.muted)
                            .multilineTextAlignment(.leading)
                        Spacer(minLength: 0)
                    }
                    .padding(.top, 10)
                    .padding(.bottom, 9)
                    .contentShape(.rect)
                }
                .buttonStyle(PressStyle())
                .overlay(alignment: .bottom) { Hairline() }
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
        .overlay(alignment: .top) { Hairline() }
        .animation(.enter, value: selected)
    }

    /// The selected prompt set as the headline of the reply; a caret while she listens.
    private var draft: some View {
        let prompt = prompts.indices.contains(selected) ? prompts[selected] : "Tell her something."
        let tail = recorder.isRecording ? "" : " Hold the disc and answer."
        return HStack(alignment: .lastTextBaseline, spacing: 3) {
            (Text(prompt).foregroundColor(.ink) + Text(tail).foregroundColor(Color(hex: 0xA9A39A)))
                .font(.serif(32, relativeTo: .title))
                .tracking(-0.3)
                .lineSpacing(6)
            if recorder.isRecording { Caret(height: 26).padding(.bottom, 4) }
        }
        .animation(.enter, value: recorder.isRecording)
    }

    private var controls: some View {
        HStack(alignment: .bottom) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 7) {
                    Circle().fill(Color.rec).frame(width: 8, height: 8)
                    Text("REC").font(.sans(11, medium: true)).tracking(1.32).foregroundStyle(Color.rec)
                }
                .opacity(recorder.isRecording ? 1 : 0.4)
                counter
                Text(note ?? (recorder.isRecording ? "Let go to send" : "Hold to record"))
                    .font(.serifItalic(18))
                    .foregroundStyle(Color.soft)
            }
            Spacer()
            RecordDisc(live: recorder.isRecording)
                .scaleEffect(pressing ? 0.97 : 1)
                .animation(.press, value: pressing)
                .gesture(hold)
                .accessibilityElement()
                .accessibilityLabel(recorder.isRecording ? "Recording. Let go to send" : "Hold to record")
                .accessibilityAddTraits(.isButton)
                .padding(.bottom, 6)
        }
    }

    private var counter: some View {
        let s = Int(recorder.elapsed)
        return (Text(String(format: "%02d", s / 60)) + Text(":").foregroundColor(.fog) + Text(String(format: "%02d", s % 60)))
            .font(.sansLight(46))
            .monospacedDigit()
            .tracking(-0.46)
            .foregroundStyle(Color.ink)
            .accessibilityLabel("\(s) seconds")
    }

    private var hold: some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { _ in
                guard !pressing else { return }
                pressing = true
                note = nil
                session.player.stop()
                Task {
                    do {
                        try await recorder.start(allowSimulated: session.isDemo)
                        Haptics.recordStart()
                        if !pressing { finish() }
                    } catch {
                        Haptics.error()
                        note = error.localizedDescription
                    }
                }
            }
            .onEnded { _ in
                pressing = false
                if recorder.isRecording { finish() }
            }
    }

    private func finish() {
        let result = recorder.stop()
        Haptics.recordStop()
        guard result.duration >= 0.8 else {
            if let url = result.url { try? FileManager.default.removeItem(at: url) }
            note = "Hold a little longer"
            return
        }
        Task { await session.send(recording: result.url, replyTo: message?.id) }
        sent()
    }
}
