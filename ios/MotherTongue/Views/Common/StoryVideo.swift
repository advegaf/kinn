import AVFoundation
import SwiftUI

/// A muted, looping story film from the videos bucket, with the thumbnail as a poster while it loads.
struct StoryVideo: View {
    @Environment(AppSession.self) private var session
    var path: String
    var thumbPath: String?

    var body: some View {
        GeometryReader { geo in
            ZStack {
                poster
                if let url = session.videoURL(path) {
                    LoopingVideo(url: url)
                }
            }
            .frame(width: geo.size.width, height: geo.size.height)
            .clipped()
        }
    }

    @ViewBuilder private var poster: some View {
        if let thumbPath, let url = session.videoURL(thumbPath) {
            AsyncImage(url: url) { phase in
                if case .success(let image) = phase {
                    image.resizable().scaledToFill()
                } else {
                    Color.night
                }
            }
        } else {
            Color.night
        }
    }
}

struct LoopingVideo: UIViewRepresentable {
    var url: URL

    func makeUIView(context: Context) -> PlayerView {
        let view = PlayerView()
        view.play(url)
        return view
    }

    func updateUIView(_ view: PlayerView, context: Context) {
        if view.url != url { view.play(url) }
    }

    static func dismantleUIView(_ view: PlayerView, coordinator: ()) {
        view.player.pause()
    }

    final class PlayerView: UIView {
        override class var layerClass: AnyClass { AVPlayerLayer.self }
        private var playerLayer: AVPlayerLayer? { layer as? AVPlayerLayer }
        let player = AVQueuePlayer()
        private var looper: AVPlayerLooper?
        private(set) var url: URL?

        override init(frame: CGRect) {
            super.init(frame: frame)
            backgroundColor = .clear
            isUserInteractionEnabled = false
            player.isMuted = true
            player.preventsDisplaySleepDuringVideoPlayback = false
            playerLayer?.player = player
            playerLayer?.videoGravity = .resizeAspectFill
        }

        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

        func play(_ url: URL) {
            self.url = url
            player.removeAllItems()
            looper = AVPlayerLooper(player: player, templateItem: AVPlayerItem(url: url))
            player.play()
        }
    }
}
