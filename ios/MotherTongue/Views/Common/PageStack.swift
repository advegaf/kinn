import SwiftUI
import UIKit

/// Pages laid on the root page like leaves in a book. Each page below stays alive, so back shows the real
/// previous page. A swipe from the leading edge drags the top page away and goes back.
struct PageStack<Route: Hashable, Root: View, Page: View>: View {
    var path: [Route]
    /// Drops the top route. The swipe calls it when the page is already off screen.
    var pop: () -> Void
    @ViewBuilder var root: Root
    @ViewBuilder var page: (Route) -> Page

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var width: CGFloat = 390
    @State private var drag: CGFloat = 0
    @State private var settling = false

    private var progress: CGFloat { width > 0 ? min(max(drag / width, 0), 1) : 0 }

    var body: some View {
        ZStack {
            layer(depth: path.count) { root }
            ForEach(Array(path.enumerated()), id: \.element) { index, route in
                layer(depth: path.count - 1 - index) { page(route) }
                    .transition(reduceMotion ? .opacity : .opacity.combined(with: .offset(x: width * 0.3)))
            }
        }
        .onGeometryChange(for: CGFloat.self) { $0.size.width } action: { width = $0 }
        .gesture(EdgePan(enabled: !path.isEmpty && !settling, changed: { drag = $0 }, ended: settle))
    }

    private func layer<Content: View>(depth: Int, @ViewBuilder content: () -> Content) -> some View {
        let top = depth == 0
        let below = depth == 1
        let parallax = reduceMotion ? 0 : -width * 0.08
        return content()
            .overlay {
                Color.black.opacity(below ? 0.08 * (1 - progress) : 0)
                    .ignoresSafeArea()
                    .allowsHitTesting(false)
            }
            .overlay(alignment: .leading) {
                LinearGradient(colors: [.clear, .black.opacity(0.14)], startPoint: .leading, endPoint: .trailing)
                    .frame(width: 14)
                    .offset(x: -14)
                    .opacity(top && drag > 0 ? 1 : 0)
                    .ignoresSafeArea()
                    .allowsHitTesting(false)
            }
            .offset(x: top ? drag : below ? parallax * (1 - progress) : parallax)
            .opacity(depth > 1 ? 0 : 1)
            .allowsHitTesting(top && !settling)
            .accessibilityHidden(!top)
    }

    /// Velocity decides first, so a short flick goes back and a slow drag held past half the page also goes back.
    private func settle(translation: CGFloat, velocity: CGFloat) {
        let commit = velocity > 300 || (translation > width * 0.5 && velocity > -100)
        let target = commit ? width : 0
        let distance = target - drag
        settling = true
        withAnimation(.interpolatingSpring(duration: 0.3, bounce: 0, initialVelocity: distance == 0 ? 0 : velocity / distance)) {
            drag = target
        } completion: {
            var still = Transaction()
            still.disablesAnimations = true
            withTransaction(still) {
                if commit { pop() }
                drag = 0
                settling = false
            }
        }
    }
}

private struct EdgePan: UIGestureRecognizerRepresentable {
    var enabled: Bool
    var changed: (CGFloat) -> Void
    var ended: (_ translation: CGFloat, _ velocity: CGFloat) -> Void

    func makeCoordinator(converter: CoordinateSpaceConverter) -> Coordinator { Coordinator() }

    func makeUIGestureRecognizer(context: Context) -> UIScreenEdgePanGestureRecognizer {
        let pan = UIScreenEdgePanGestureRecognizer()
        pan.edges = .left
        pan.delegate = context.coordinator
        return pan
    }

    func updateUIGestureRecognizer(_ pan: UIScreenEdgePanGestureRecognizer, context: Context) {
        pan.isEnabled = enabled
    }

    func handleUIGestureRecognizerAction(_ pan: UIScreenEdgePanGestureRecognizer, context: Context) {
        let x = pan.translation(in: pan.view).x
        switch pan.state {
        case .began, .changed: changed(max(0, x))
        case .ended: ended(x, pan.velocity(in: pan.view).x)
        case .cancelled, .failed: ended(0, -1)
        default: break
        }
    }

    final class Coordinator: NSObject, UIGestureRecognizerDelegate {
        /// A scroll view or a drag on the page waits until the edge swipe fails. It fails at once away from the edge.
        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer,
                               shouldBeRequiredToFailBy other: UIGestureRecognizer) -> Bool {
            other is UIPanGestureRecognizer && !(other is UIScreenEdgePanGestureRecognizer)
        }
    }
}
