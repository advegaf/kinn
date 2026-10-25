import XCTest

/// Each screen at the largest accessibility text size: nothing runs off the screen, every control stays usable.
final class DynamicTypeTests: KinnUITestCase {
    func testOnboardingAtLargestText() {
        launch(onboarded: false, textSize: Self.largestText)
        element("onboarding.begin")
        checkScreen("onboarding welcome, largest text")
    }

    func testFamilyScreensAtLargestText() {
        launch(textSize: Self.largestText)
        element("almanac.featured")
        checkScreen("week, largest text")

        element("almanac.featured").tap()
        element("entry.back")
        checkScreen("entry, largest text")

        element("entry.writeBack").tap()
        element("writeBack.back")
        checkScreen("write back, largest text")
        element("writeBack.back").tap()

        element("tabBar.settings").tap()
        element("settings.done")
        checkScreen("settings, largest text")
    }
}
