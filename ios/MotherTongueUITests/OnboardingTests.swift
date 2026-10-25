import XCTest

/// First launch as Angel: name, demo mode, go on without pairing, skip the voice, land on the week.
final class OnboardingTests: KinnUITestCase {
    func testOnboardingInDemoMode() {
        launch(onboarded: false)
        let begin = element("onboarding.begin")
        XCTAssertFalse(begin.isEnabled, "Connect works with no name")

        let name = element("onboarding.name")
        name.tap()
        name.typeText("Angel\n")
        flip("onboarding.demoMode")
        waitFor(app.switches["onboarding.demoMode"], "value == '1'", timeout: 3, "demo mode does not turn on")
        checkScreen("onboarding welcome")

        begin.tap()
        let skipPairing = element("onboarding.skipPairing")
        checkScreen("onboarding pair")

        skipPairing.tap()
        element("onboarding.skip")
        checkScreen("onboarding voice")
        element("onboarding.skip").tap()

        element("almanac.featured", timeout: 15)
    }
}
