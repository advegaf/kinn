import SwiftUI

/// A story still. `demo/<name>` paths load from the asset catalog, others from the images bucket.
/// Fills its frame, cropping around `focus`.
struct StoryImage: View {
    @Environment(AppSession.self) private var session
    var path: String
    var focus: UnitPoint = .center

    var body: some View {
        GeometryReader { geo in
            Group {
                if path.hasPrefix("demo/") {
                    fill(Image(String(path.dropFirst(5))), in: geo.size)
                } else {
                    AsyncImage(url: session.imageURL(path), transaction: Transaction(animation: .easeOut(duration: 2))) { phase in
                        if case .success(let image) = phase {
                            fill(image, in: geo.size)
                        } else {
                            Color.night
                        }
                    }
                }
            }
            .frame(width: geo.size.width, height: geo.size.height)
            .clipped()
        }
    }

    /// Aspect fill, then shift the overflow so `focus` stays in view.
    private func fill(_ image: Image, in size: CGSize) -> some View {
        image.resizable()
            .scaledToFill()
            .frame(width: size.width, height: size.height, alignment: Alignment(horizontal: horizontal, vertical: vertical))
    }

    private var horizontal: HorizontalAlignment {
        focus.x < 0.25 ? .leading : focus.x > 0.75 ? .trailing : .center
    }

    private var vertical: VerticalAlignment {
        focus.y < 0.25 ? .top : focus.y > 0.75 ? .bottom : .center
    }
}
