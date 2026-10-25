import SwiftUI

struct KinnTabBar: View {
    var home: () -> Void
    var archive: () -> Void
    var compose: () -> Void
    var settings: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            Hairline()
            HStack(spacing: 0) {
                item("Home", selected: true, action: home)
                item("Archive", action: archive)
                item("New note", action: compose)
                item("Settings", action: settings)
            }
            .padding(.horizontal, 30)
            .padding(.top, 6)
        }
        .background { Color.paper.ignoresSafeArea(edges: .bottom) }
    }

    /// The bar only shows on the week, so Home is always the selected item.
    private func item(_ label: String, selected: Bool = false, action: @escaping () -> Void) -> some View {
        Button {
            Haptics.tap()
            action()
        } label: {
            Text(label)
                .font(.serif(19))
                .foregroundStyle(selected ? Color.ink : Color.soft)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
                .frame(maxWidth: .infinity, minHeight: 44)
                .contentShape(.rect)
        }
        .buttonStyle(PressStyle())
        .accessibilityAddTraits(selected ? .isSelected : [])
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
