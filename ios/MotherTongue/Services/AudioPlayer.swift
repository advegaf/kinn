import AVFoundation
import Observation

enum PlaybackSource: Equatable {
    case url(URL)
    case speech(text: String, lang: String)
}

@Observable
@MainActor
final class AudioPlayer: NSObject {
    private(set) var currentKey: String?
    private(set) var isPlaying = false
    private(set) var progress: Double = 0
    /// Real length of the playing file, once AVPlayer knows it. Nil for speech.
    private(set) var duration: Double?

    private var player: AVPlayer?
    private var timeObserver: Any?
    private var endObserver: NSObjectProtocol?
    private let synth = AVSpeechSynthesizer()
    private var speechLength = 1
    private var speechText = ""
    private var speechLang = "en"
    private var speechOffset = 0
    private var utteranceID: ObjectIdentifier?
    private var pendingSeek: Double?
    var onFinish: ((String) -> Void)?

    override init() {
        super.init()
        synth.delegate = self
    }

    func toggle(_ source: PlaybackSource, key: String) {
        if currentKey == key && isPlaying { stop() } else { play(source, key: key) }
    }

    func play(_ source: PlaybackSource, key: String) {
        stop()
        try? AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetoothA2DP])
        try? AVAudioSession.sharedInstance().setActive(true)
        currentKey = key
        isPlaying = true
        progress = 0
        duration = nil
        switch source {
        case .url(let url):
            let item = AVPlayerItem(url: url)
            let player = AVPlayer(playerItem: item)
            self.player = player
            timeObserver = player.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.05, preferredTimescale: 600), queue: .main) { [weak self] time in
                MainActor.assumeIsolated {
                    guard let self, let item = self.player?.currentItem else { return }
                    let total = item.duration.seconds
                    if total.isFinite, total > 0 {
                        self.duration = total
                        if let f = self.pendingSeek {
                            self.pendingSeek = nil
                            self.seek(to: f)
                            return
                        }
                        self.progress = min(1, time.seconds / total)
                    }
                }
            }
            endObserver = NotificationCenter.default.addObserver(forName: AVPlayerItem.didPlayToEndTimeNotification, object: item, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { self?.finish() }
            }
            player.play()
        case .speech(let text, let lang):
            speechText = text
            speechLang = lang
            speechLength = max(1, (text as NSString).length)
            speak(from: 0)
        }
    }

    /// Jump to a fraction of the narration. AVPlayer seeks; speech restarts from that character,
    /// which is exact enough because beats are cut on character offsets too.
    func seek(to fraction: Double) {
        guard isPlaying else { return }
        let f = min(max(fraction, 0), 1)
        if let player {
            guard let total = player.currentItem?.duration.seconds, total.isFinite, total > 0 else {
                pendingSeek = f
                return
            }
            progress = f
            player.seek(to: CMTime(seconds: total * f, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero)
        } else {
            utteranceID = nil
            synth.stopSpeaking(at: .immediate)
            speak(from: Int((f * Double(speechLength)).rounded()))
        }
    }

    private func speak(from offset: Int) {
        let full = speechText as NSString
        let start = min(max(0, offset), full.length)
        let utterance = AVSpeechUtterance(string: full.substring(from: start))
        utterance.voice = AVSpeechSynthesisVoice(language: speechLang == "es" ? "es-MX" : "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate * 0.95
        speechOffset = start
        progress = Double(start) / Double(speechLength)
        utteranceID = ObjectIdentifier(utterance)
        synth.speak(utterance)
    }

    func stop() {
        if let timeObserver { player?.removeTimeObserver(timeObserver) }
        if let endObserver { NotificationCenter.default.removeObserver(endObserver) }
        timeObserver = nil
        endObserver = nil
        player?.pause()
        player = nil
        utteranceID = nil
        pendingSeek = nil
        if synth.isSpeaking { synth.stopSpeaking(at: .immediate) }
        isPlaying = false
        currentKey = nil
        progress = 0
        duration = nil
    }

    private func finish() {
        let key = currentKey
        progress = 1
        stop()
        if let key { onFinish?(key) }
    }

    fileprivate func speechProgress(_ location: Int, id: ObjectIdentifier) {
        guard id == utteranceID else { return }
        progress = min(1, Double(speechOffset + location) / Double(speechLength))
    }

    fileprivate func speechDone(id: ObjectIdentifier) {
        guard id == utteranceID else { return }
        finish()
    }
}

extension AudioPlayer: AVSpeechSynthesizerDelegate {
    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        let id = ObjectIdentifier(utterance)
        Task { @MainActor in self.speechDone(id: id) }
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, willSpeakRangeOfSpeechString characterRange: NSRange, utterance: AVSpeechUtterance) {
        let loc = characterRange.location + characterRange.length
        let id = ObjectIdentifier(utterance)
        Task { @MainActor in self.speechProgress(loc, id: id) }
    }
}
