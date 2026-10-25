import UIKit

@MainActor
enum Haptics {
    static func recordStart() { UIImpactFeedbackGenerator(style: .medium).impactOccurred() }
    static func recordStop() { UIImpactFeedbackGenerator(style: .soft).impactOccurred() }
    static func arrival() { UINotificationFeedbackGenerator().notificationOccurred(.success) }
    static func tap() { UISelectionFeedbackGenerator().selectionChanged() }
    static func error() { UINotificationFeedbackGenerator().notificationOccurred(.error) }
}
