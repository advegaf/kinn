import XCTest

/// Launches the Almanac in demo mode and checks the mobile basics on each screen it reaches.
@MainActor
class KinnUITestCase: XCTestCase {
    let app = XCUIApplication()

    static let largestText = "UICTContentSizeCategoryAccessibilityXXXL"

    /// Every launch starts from a fresh install, so no state leaks between tests.
    func launch(onboarded: Bool = true, textSize: String? = nil, _ extra: [String] = []) {
        continueAfterFailure = false
        var args = ["-uiTestReset"]
        if onboarded {
            args += ["-demoMode", "YES", "-onboarded", "YES", "-role", "family", "-name", "Angel", "-lang", "en"]
        }
        if let textSize { args += ["-UIPreferredContentSizeCategoryName", textSize] }
        app.launchArguments = args + extra
        app.launch()
    }

    @discardableResult
    func element(_ id: String, timeout: TimeInterval = 10) -> XCUIElement {
        let match = app.descendants(matching: .any).matching(identifier: id).firstMatch
        XCTAssertTrue(match.waitForExistence(timeout: timeout), "\(id) did not appear")
        return match
    }

    func waitGone(_ id: String, timeout: TimeInterval = 5) {
        let match = app.descendants(matching: .any).matching(identifier: id).firstMatch
        let gone = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: match)
        XCTAssertEqual(XCTWaiter.wait(for: [gone], timeout: timeout), .completed, "\(id) is still on screen")
    }

    func waitFor(_ element: XCUIElement, _ format: String, timeout: TimeInterval = 10, _ message: String) {
        let done = XCTNSPredicateExpectation(predicate: NSPredicate(format: format), object: element)
        XCTAssertEqual(XCTWaiter.wait(for: [done], timeout: timeout), .completed, message)
    }

    /// Taps a switch on its knob. A tap on the centre of a labelled SwiftUI toggle can miss it.
    func flip(_ id: String) {
        element(id).coordinate(withNormalizedOffset: CGVector(dx: 0.95, dy: 0.5)).tap()
    }

    /// Saves a screenshot, then checks touch targets, safe areas, text that runs off the screen, and clipped text.
    func checkScreen(_ name: String) {
        // Let the screen's enter animation settle before the frames are read.
        _ = app.wait(for: .runningForeground, timeout: 1)
        Thread.sleep(forTimeInterval: 0.8)
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = name
        shot.lifetime = .keepAlways
        add(shot)

        // Frame checks cannot see text cut off by its container or truncated to "...".
        var issues: [String] = []
        do {
            try app.performAccessibilityAudit(for: [.textClipped, .dynamicType]) { issue in
                let id = issue.element.map { $0.identifier.isEmpty ? $0.label : $0.identifier } ?? "?"
                issues.append("\(id): \(issue.compactDescription)")
                return true
            }
        } catch {
            issues.append("accessibility audit did not run: \(error)")
        }
        XCTAssertTrue(issues.isEmpty, "\(name): " + issues.joined(separator: "; "))

        let window = app.windows.firstMatch.frame
        let insets = safeInsets(window)
        for button in app.buttons.allElementsBoundByIndex where button.exists && button.isHittable {
            let f = button.frame
            let label = "\(name): button \(button.identifier.isEmpty ? button.label : button.identifier)"
            XCTAssertGreaterThanOrEqual(f.height.rounded(), 44, "\(label) is \(Int(f.height)) pt high")
            XCTAssertGreaterThanOrEqual(f.width.rounded(), 44, "\(label) is \(Int(f.width)) pt wide")
            XCTAssertGreaterThanOrEqual(f.minY, window.minY + insets.top - 1, "\(label) is under the status bar")
            XCTAssertLessThanOrEqual(f.maxY, window.maxY - insets.bottom + 1, "\(label) is under the home indicator")
        }
        for text in app.staticTexts.allElementsBoundByIndex where text.exists && text.isHittable {
            let f = text.frame
            XCTAssertGreaterThanOrEqual(f.minX, window.minX - 1, "\(name): \"\(text.label)\" runs off the left edge")
            XCTAssertLessThanOrEqual(f.maxX, window.maxX + 1, "\(name): \"\(text.label)\" runs off the right edge")
        }
    }

    /// The status bar lives in SpringBoard. Face ID phones keep 34 pt at the bottom for the home indicator.
    private func safeInsets(_ window: CGRect) -> (top: CGFloat, bottom: CGFloat) {
        let bar = XCUIApplication(bundleIdentifier: "com.apple.springboard").statusBars.firstMatch
        let top = bar.exists ? bar.frame.maxY : 0
        return (top, top > 20 ? 34 : 0)
    }

    /// Mean brightness 0...1 of a small patch of the screen, at a point given as fractions of its size.
    func brightness(atX x: CGFloat, y: CGFloat) -> CGFloat {
        guard let image = app.screenshot().image.cgImage else { return -1 }
        let rect = CGRect(x: CGFloat(image.width) * x - 4, y: CGFloat(image.height) * y - 4, width: 8, height: 8)
        guard let patch = image.cropping(to: rect),
              let ctx = CGContext(data: nil, width: 1, height: 1, bitsPerComponent: 8, bytesPerRow: 4,
                                  space: CGColorSpaceCreateDeviceRGB(),
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue),
              let data = ctx.data else { return -1 }
        ctx.interpolationQuality = .medium
        ctx.draw(patch, in: CGRect(x: 0, y: 0, width: 1, height: 1))
        let px = data.bindMemory(to: UInt8.self, capacity: 4)
        return (CGFloat(px[0]) + CGFloat(px[1]) + CGFloat(px[2])) / (3 * 255)
    }
}
