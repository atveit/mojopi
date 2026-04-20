import SwiftUI

@main
struct MojopiApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 600, minHeight: 500)
        }
        .windowStyle(.titleBar)
        .commands {
            CommandGroup(after: .newItem) {
                Button("New Session") {
                    NotificationCenter.default.post(name: .newSession, object: nil)
                }
                .keyboardShortcut("n", modifiers: .command)
                Button("Clear") {
                    NotificationCenter.default.post(name: .clearSession, object: nil)
                }
                .keyboardShortcut("k", modifiers: .command)
            }
        }
    }
}

extension Notification.Name {
    static let newSession = Notification.Name("newSession")
    static let clearSession = Notification.Name("clearSession")
}
