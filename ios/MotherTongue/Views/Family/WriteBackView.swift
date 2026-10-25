import SwiftUI

/// 03 writing back: her line quoted when replying, three prompts in the margin, and a disc to tap or hold while you talk.
struct WriteBackView: View {
    var message: Message?
    var back: () -> Void
    var sent: () -> Void

    @Environment(AppSession.self) private var session
    @State private var selected = 0
    @State private var pressStart: Date?
    /// A short tap leaves the recording running until the next tap.
    @State private var latched = false
    @State private var note: String?

    private var recorder: AudioRecorder { session.recorder }
    private var prompts: [String] {
        let asked = Array((message?.askAbout ?? []).prefix(3))
        return asked.isEmpty ? ["Tell her about your day", "Tell her what you ate", "Tell her what made you laugh"] : asked
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            BackButton(action: back)
                .accessibilityIdentifier("writeBack.back")
            head
                .padding(.top, 8)
            if let message {
                Text(Almanac.quote(message))
                    .font(.serif(22))
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
        .contentShape(.rect)
        .background { PaperCanvas() }
        .onDisappear { recorder.cancel() }
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
                            .foregroundStyle(on ? Color.ink : Color.sub)
                            .frame(width: 44, alignment: .leading)
                        Text(prompt)
                            .font(.serif(19))
                            .foregroundStyle(on ? Color.ink : Color.sub)
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
                .accessibilityIdentifier("writeBack.prompt")
            }
        }
        .overlay(alignment: .top) { Hairline() }
        .animation(.enter, value: selected)
    }

    /// The selected prompt set as the headline of the reply; a caret while she listens.
    private var draft: some View {
        let prompt = prompts.indices.contains(selected) ? prompts[selected] : "Tell her something."
        let stop = prompt.last.map { ".?!".contains($0) } == true ? "" : "."
        let tail = recorder.isRecording ? "" : "\(stop) Tap the disc and answer."
        return HStack(alignment: .lastTextBaseline, spacing: 3) {
            (Text(prompt).foregroundColor(.ink) + Text(tail).foregroundColor(.later))
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
                HStack(spacing: 10) {
                    counter
                    Circle().fill(Color.rec).frame(width: 8, height: 8)
                        .opacity(recorder.isRecording ? 1 : 0)
                        .accessibilityHidden(true)
                }
                Text(note ?? hint)
                    .font(.serif(18))
                    .foregroundStyle(Color.soft)
            }
            Spacer()
            RecordDisc(live: recorder.isRecording)
                .scaleEffect(pressStart != nil ? 0.97 : 1)
                .animation(.press, value: pressStart != nil)
                .gesture(press)
                .accessibilityElement()
                .accessibilityLabel(recorder.isRecording ? "Recording. Tap to send" : "Record")
                .accessibilityAddTraits(.isButton)
                .accessibilityIdentifier("writeBack.record")
                .accessibilityAction {
                    if recorder.isRecording {
                        latched = false
                        finish()
                    } else {
                        latched = true
                        begin()
                    }
                }
                .padding(.bottom, 6)
        }
    }

    private var hint: String {
        if !recorder.isRecording { return "Tap to record, tap again to send" }
        return latched ? "Tap again to send" : "Let go to send"
    }

    private var counter: some View {
        let s = Int(recorder.elapsed)
        return (Text(String(format: "%02d", s / 60)) + Text(":").foregroundColor(.sub) + Text(String(format: "%02d", s % 60)))
            .font(.sansLight(46))
            .monospacedDigit()
            .tracking(-0.46)
            .foregroundStyle(Color.ink)
            .accessibilityLabel(recorder.isRecording ? "Recording, \(s) seconds" : "\(s) seconds")
    }

    /// Under 0.3 s is a tap that toggles; anything longer records while held.
    private var press: some Gesture {
        DragGesture(minimumDistance: 0)
            .onChanged { _ in
                guard pressStart == nil else { return }
                pressStart = .now
                if !latched { begin() }
            }
            .onEnded { _ in
                let held = Date.now.timeIntervalSince(pressStart ?? .now)
                pressStart = nil
                if latched {
                    latched = false
                    if recorder.isRecording { finish() }
                } else if held < 0.3 {
                    latched = true
                } else if recorder.isRecording {
                    finish()
                }
            }
    }

    private func begin() {
        note = nil
        session.player.stop()
        Task {
            do {
                try await recorder.start(allowSimulated: session.isDemo)
                Haptics.recordStart()
                if pressStart == nil && !latched { finish() }
            } catch {
                Haptics.error()
                latched = false
                note = error.localizedDescription
            }
        }
    }

    private func finish() {
        let result = recorder.stop()
        Haptics.recordStop()
        guard result.duration >= 0.8 else {
            if let url = result.url { try? FileManager.default.removeItem(at: url) }
            note = "Too short. Say a little more"
            return
        }
        Task { await session.send(recording: result.url, replyTo: message?.id) }
        sent()
    }
}
