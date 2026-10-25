import XCTest

/// The demo path on the grandchild's side: open Margaret's story, hear it, write back, and settings.
final class AlmanacTests: KinnUITestCase {
    func testWeek() {
        launch()
        element("tabBar.settings")
        element("almanac.featured")
        element("almanac.listen")
        XCTAssertGreaterThan(app.buttons.matching(identifier: "almanac.row").count, 0, "the index has no older stories")
        checkScreen("week")
    }

    func testOpenEntryPlaysAndGoesBack() {
        launch()
        element("almanac.listen").tap()
        element("entry.back")
        let track = element("entry.track")
        waitFor(track, "value != '0 percent'", timeout: 15, "the story does not play")
        checkScreen("entry playing")

        let original = element("entry.original")
        let english = original.label
        original.tap()
        waitFor(original, "label != '\(english)'", "Hear her original does not switch to her voice")

        element("entry.back").tap()
        waitGone("entry.back")
        element("tabBar.settings")
    }

    func testOpenOlderStoryFromIndex() {
        launch()
        app.buttons.matching(identifier: "almanac.row").firstMatch.tap()
        element("entry.back")
        checkScreen("entry from index")
        element("entry.back").tap()
        element("tabBar.settings")
    }

    func testWriteBackSendsAndGoesBack() {
        launch()
        element("almanac.featured").tap()
        element("entry.writeBack").tap()
        element("writeBack.back")
        let prompts = app.buttons.matching(identifier: "writeBack.prompt")
        if prompts.count > 1 {
            prompts.element(boundBy: 1).tap()
            waitFor(prompts.element(boundBy: 1), "selected == true", timeout: 3, "a tapped prompt is not selected")
        }
        checkScreen("write back")

        // Back from write back returns to the story it answers.
        element("writeBack.back").tap()
        waitGone("writeBack.back")
        element("entry.writeBack").tap()
        // A hold records while held, and letting go sends.
        element("writeBack.record").press(forDuration: 2.5)
        checkNoteSends()
    }

    func testNewNoteSends() {
        launch()
        element("tabBar.compose").tap()
        element("writeBack.back")
        XCTAssertGreaterThan(app.buttons.matching(identifier: "writeBack.prompt").count, 0, "a new note has no prompts")
        checkScreen("new note")
        // A tap starts the recording and the next tap sends it.
        let record = element("writeBack.record")
        record.tap()
        Thread.sleep(forTimeInterval: 1.5)
        record.tap()
        checkNoteSends()
    }

    func testTooShortDoesNotSend() {
        launch()
        element("tabBar.compose").tap()
        element("writeBack.record").doubleTap()
        Thread.sleep(forTimeInterval: 1)
        XCTAssertTrue(element("writeBack.back").exists, "a too short note left the page")
        XCTAssertFalse(app.descendants(matching: .any)["almanac.pending"].exists, "a too short note was sent")
    }

    /// Back on the week, the note shows as on its way, then it lands with no retry offer.
    private func checkNoteSends() {
        element("tabBar.settings")
        element("almanac.pending", timeout: 5)
        checkScreen("week after send")
        waitGone("almanac.pending", timeout: 20)
        XCTAssertFalse(app.buttons["almanac.retry"].exists, "the note did not send")
    }

    func testSettingsAndBack() {
        launch()
        element("tabBar.settings").tap()
        element("settings.done")
        XCTAssertEqual(app.switches["settings.demoMode"].value as? String, "1", "demo mode is not on")
        element("settings.startOver")
        checkScreen("settings")
        element("settings.done").tap()
        waitGone("settings.done")
        element("tabBar.settings")
    }

    /// The app sets its own paper and night look. A dark system setting must not change it.
    func testColorSchemeIsFixed() {
        launch()
        element("almanac.featured")
        Thread.sleep(forTimeInterval: 1)
        XCTAssertGreaterThan(brightness(atX: 0.5, y: 0.97), 0.7, "the week page is not on light paper")
        element("almanac.listen").tap()
        element("entry.back")
        Thread.sleep(forTimeInterval: 1.5)
        XCTAssertLessThan(brightness(atX: 0.5, y: 0.97), 0.3, "the entry page is not dark")
        checkScreen("entry color scheme")
    }
}
