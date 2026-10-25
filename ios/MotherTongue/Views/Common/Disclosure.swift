import SwiftUI

struct SectionTitle: View {
    var text: String
    var body: some View {
        Text(text)
            .font(.serif(26, relativeTo: .title3))
            .foregroundStyle(Color.ink)
    }
}

/// A section that starts closed. A tap on its title opens it.
struct Disclosure<Content: View>: View {
    var title: String
    var id: String
    @ViewBuilder var content: Content

    @State private var open = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @ScaledMetric(relativeTo: .body) private var chevron: CGFloat = 13

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                Haptics.tap()
                let animation: Animation? = reduceMotion ? nil : open ? .pop : .push
                withAnimation(animation) { open.toggle() }
            } label: {
                HStack(spacing: 16) {
                    SectionTitle(text: title)
                    Spacer(minLength: 0)
                    Chevron()
                        .stroke(style: StrokeStyle(lineWidth: 1.25, lineCap: .round, lineJoin: .round))
                        .frame(width: chevron * 0.5, height: chevron)
                        .rotationEffect(.degrees(open ? 90 : -90))
                        .frame(width: chevron, height: chevron * 0.5)
                        .foregroundStyle(Color.ink)
                        .accessibilityHidden(true)
                }
                .padding(.bottom, 10)
                .tapTarget()
            }
            .buttonStyle(PressStyle())
            .accessibilityValue(open ? "Expanded" : "Collapsed")
            .accessibilityIdentifier(id)
            Hairline()
            if open {
                VStack(alignment: .leading, spacing: 0) { content }
                    .transition(reduceMotion ? .fadeIn : .opacity)
            }
        }
    }
}
