import AVFoundation
import MediaPlayer
import SwiftUI

/// Treats a volume-up press (what cheap Bluetooth camera-shutter remotes send) as a Hearth button press.
/// Self-contained: delete this file and its single use in HearthView to drop the feature.
struct VolumeButtonTrigger: UIViewRepresentable {
    var onPress: @MainActor () -> Void

    func makeUIView(context: Context) -> VolumeWatcherView {
        let view = VolumeWatcherView()
        view.onPress = onPress
        return view
    }

    func updateUIView(_ view: VolumeWatcherView, context: Context) {
        view.onPress = onPress
    }
}

final class VolumeWatcherView: UIView {
    var onPress: (@MainActor () -> Void)?
    private var observation: NSKeyValueObservation?
    private let volumeView = MPVolumeView(frame: CGRect(x: -200, y: -200, width: 10, height: 10))
    private var resetting = false
    private let resting: Float = 0.5

    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        volumeView.alpha = 0.01
        addSubview(volumeView)
        try? AVAudioSession.sharedInstance().setActive(true)
        setVolume(resting)
        observation = AVAudioSession.sharedInstance().observe(\.outputVolume, options: [.new, .old]) { [weak self] _, change in
            let new = change.newValue ?? 0
            let old = change.oldValue ?? 0
            Task { @MainActor in self?.volumeChanged(from: old, to: new) }
        }
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    private func volumeChanged(from old: Float, to new: Float) {
        if resetting {
            resetting = false
            return
        }
        guard new > old || new >= 0.99 else { return }
        onPress?()
        setVolume(resting)
    }

    private func setVolume(_ value: Float) {
        guard let slider = volumeView.subviews.compactMap({ $0 as? UISlider }).first else { return }
        resetting = abs(AVAudioSession.sharedInstance().outputVolume - value) > 0.001
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { slider.value = value }
    }

    deinit { observation?.invalidate() }
}
