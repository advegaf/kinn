import SwiftUI

struct KinnTabBar: View {
    var home: () -> Void
    var compose: () -> Void
    var settings: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            Hairline()
            HStack(spacing: 0) {
                item("Home", action: home)
                item("New note", action: compose)
                item("Settings", action: settings)
            }
            .padding(.horizontal, 30)
            .padding(.top, 6)
        }
        .background { Color.paper.ignoresSafeArea(edges: .bottom) }
    }

    private func item(_ label: String, action: @escaping () -> Void) -> some View {
        Button {
            Haptics.tap()
            action()
        } label: {
            Text(label)
                .font(.serif(19))
                .foregroundStyle(Color.ink)
                .frame(maxWidth: .infinity, minHeight: 44)
                .contentShape(.rect)
        }
        .buttonStyle(PressStyle())
    }
}

extension View {
    func kinnTabBar(home: @escaping () -> Void, compose: @escaping () -> Void, settings: @escaping () -> Void) -> some View {
        safeAreaInset(edge: .bottom, spacing: 0) {
            KinnTabBar(home: home, compose: compose, settings: settings)
        }
    }
}
