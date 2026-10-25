import SwiftUI

struct KinnTabBar: View {
    var home: () -> Void
    var archive: () -> Void
    var compose: () -> Void
    var settings: () -> Void

    /// Instrument Serif's descender is 0.04 em deeper than the space over its cap height, so the ink sits centered with 0.04 em more on top.
    @ScaledMetric(relativeTo: .body) private var nudge: CGFloat = 0.76

    var body: some View {
        HStack(spacing: 0) {
            Spacer(minLength: 0)
            item("Home", id: "tabBar.home", selected: true, action: home)
            Spacer(minLength: 0)
            item("Archive", id: "tabBar.archive", action: archive)
            Spacer(minLength: 0)
            item("New note", id: "tabBar.compose", action: compose)
            Spacer(minLength: 0)
            item("Settings", id: "tabBar.settings", action: settings)
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 8)
        .overlay(alignment: .top) { Hairline() }
        .background { Color.paper.ignoresSafeArea(edges: .bottom) }
    }

    /// The bar only shows on the week, so Home is always the selected item.
    /// Fixed padding: measuring the bar's own safe area inset and padding by it changed the inset again, a layout loop that froze the app.
    private func item(_ label: String, id: String, selected: Bool = false, action: @escaping () -> Void) -> some View {
        Button {
            Haptics.tap()
            action()
        } label: {
            Text(label)
                .font(.serif(19))
                .foregroundStyle(selected ? Color.ink : Color.soft)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .padding(.horizontal, 8)
                .padding(.top, 14 + nudge)
                .padding(.bottom, 6)
                .frame(minHeight: 44)
                .contentShape(.rect)
        }
        .buttonStyle(PressStyle())
        .accessibilityAddTraits(selected ? .isSelected : [])
        .accessibilityIdentifier(id)
    }
}

extension View {
    func kinnTabBar(home: @escaping () -> Void, archive: @escaping () -> Void, compose: @escaping () -> Void,
                    settings: @escaping () -> Void) -> some View {
        safeAreaInset(edge: .bottom, spacing: 0) {
            KinnTabBar(home: home, archive: archive, compose: compose, settings: settings)
        }
    }
}
