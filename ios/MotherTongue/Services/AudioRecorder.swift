import AVFoundation
import Observation

@Observable
@MainActor
final class AudioRecorder {
    private(set) var isRecording = false
    private(set) var level: Float = 0
    private(set) var levels: [Float] = Array(repeating: 0, count: 48)
    private(set) var elapsed: TimeInterval = 0

    private var recorder: AVAudioRecorder?
    private var meterTask: Task<Void, Never>?
    private var startDate: Date?
    private var simulated = false

    enum RecorderError: LocalizedError {
        case permissionDenied
        var errorDescription: String? { "Microphone access is off. Turn it on in Settings." }
    }

    static func requestPermission() async -> Bool {
        await AVAudioApplication.requestRecordPermission()
    }

    func start(allowSimulated: Bool = false) async throws {
        guard !isRecording else { return }
        do {
            guard await Self.requestPermission() else { throw RecorderError.permissionDenied }
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetoothA2DP])
            try session.setActive(true)
            let url = FileManager.default.temporaryDirectory.appending(path: "rec-\(UUID().uuidString).m4a")
            let settings: [String: Any] = [
                AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
                AVSampleRateKey: 44_100,
                AVNumberOfChannelsKey: 1,
                AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
            ]
            let rec = try AVAudioRecorder(url: url, settings: settings)
            rec.isMeteringEnabled = true
            guard rec.record() else { throw CocoaError(.fileWriteUnknown) }
            recorder = rec
            simulated = false
        } catch {
            guard allowSimulated else { throw error }
            simulated = true
        }
        isRecording = true
        startDate = .now
        elapsed = 0
        levels = Array(repeating: 0, count: levels.count)
        startMetering()
    }

    #if DEBUG
    /// Screenshot aid: a simulated recording with no mic or permission prompt.
    func startFake() {
        guard !isRecording else { return }
        simulated = true
        isRecording = true
        startDate = .now.addingTimeInterval(-7)
        startMetering()
    }
    #endif

    /// Returns the recorded file, or nil when the recording was simulated (demo mode without a mic).
    @discardableResult
    func stop() -> (url: URL?, duration: TimeInterval) {
        meterTask?.cancel()
        meterTask = nil
        let duration = startDate.map { Date.now.timeIntervalSince($0) } ?? 0
        let url = simulated ? nil : recorder?.url
        recorder?.stop()
        recorder = nil
        isRecording = false
        level = 0
        startDate = nil
        return (url, duration)
    }

    func cancel() {
        let result = stop()
        if let url = result.url { try? FileManager.default.removeItem(at: url) }
    }

    private func startMetering() {
        meterTask = Task { [weak self] in
            while !Task.isCancelled {
                self?.tick()
                try? await Task.sleep(for: .milliseconds(60))
            }
        }
    }

    private func tick() {
        var value: Float
        if let recorder, !simulated {
            recorder.updateMeters()
            let db = recorder.averagePower(forChannel: 0)
            value = max(0, min(1, (db + 50) / 50))
        } else {
            value = Float.random(in: 0.15...0.8)
        }
        value = level * 0.4 + value * 0.6
        level = value
        levels.removeFirst()
        levels.append(value)
        if let startDate { elapsed = Date.now.timeIntervalSince(startDate) }
    }
}
