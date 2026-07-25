import XCTest

final class RemoteShellUITests: XCTestCase {
  override func setUpWithError() throws {
    continueAfterFailure = false
  }

  @MainActor
  func testTerminalStartupCommandAndRelaunch() throws {
    let app = XCUIApplication()
    app.launch()

    XCTAssertTrue(
      app.wait(for: .runningForeground, timeout: 20),
      "RemoteShell did not reach the foreground"
    )
    XCTAssertTrue(
      app.windows.firstMatch.waitForExistence(timeout: 10),
      "RemoteShell did not create a window"
    )

    attachDiagnostics(for: app, name: "first-launch")

    let terminal = app.webViews.firstMatch
    if terminal.waitForExistence(timeout: 10) && terminal.isHittable {
      terminal.tap()
    } else {
      app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.45)).tap()
    }

    app.typeText("echo REMOTESHELL_UI_SMOKE_OK\n")
    sleep(5)

    XCTAssertEqual(
      app.state,
      .runningForeground,
      "RemoteShell terminated after terminal input"
    )
    attachDiagnostics(for: app, name: "after-local-command")

    app.terminate()
    app.launch()

    XCTAssertTrue(
      app.wait(for: .runningForeground, timeout: 20),
      "RemoteShell did not survive relaunch"
    )
    XCTAssertTrue(
      app.windows.firstMatch.waitForExistence(timeout: 10),
      "RemoteShell did not restore a window"
    )

    sleep(5)
    XCTAssertEqual(app.state, .runningForeground)
    attachDiagnostics(for: app, name: "relaunch")
  }

  @MainActor
  private func attachDiagnostics(for app: XCUIApplication, name: String) {
    let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
    screenshot.name = name
    screenshot.lifetime = .keepAlways
    add(screenshot)

    let hierarchy = XCTAttachment(string: app.debugDescription)
    hierarchy.name = "\(name)-accessibility.txt"
    hierarchy.lifetime = .keepAlways
    add(hierarchy)
  }
}
