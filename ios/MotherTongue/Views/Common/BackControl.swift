import SwiftUI

/// The one back control on every page that is not home: a thin chevron and a serif word.
struct BackButton: View {
    var title = "Back"
    var color: Color = .ink
    var action: () -> Void
    @ScaledMetric(relativeTo: .body) private var chevron: CGFloat = 13

    var body: some View {
        Button {
            Haptics.tap()
            action()
        } label: {
            HStack(spacing: 8) {
                Chevron()
                    .stroke(style: StrokeStyle(lineWidth: 1.25, lineCap: .round, lineJoin: .round))
                    .frame(width: chevron * 0.5, height: chevron)
                    .accessibilityHidden(true)
                Text(title).font(.serif(19))
            }
            .foregroundStyle(color)
            .frame(minWidth: 44, minHeight: 44, alignment: .leading)
            .contentShape(.rect)
        }
        .buttonStyle(PressStyle())
        .accessibilityLabel(title)
    }
}

private struct Chevron: Shape {
    func path(in rect: CGRect) -> Path {
        Path { p in
            p.move(to: CGPoint(x: rect.maxX, y: rect.minY))
            p.addLine(to: CGPoint(x: rect.minX, y: rect.midY))
            p.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        }
    }
}
