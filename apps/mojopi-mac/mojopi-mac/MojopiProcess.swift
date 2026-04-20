import Foundation
import Combine

enum MojopiEvent {
    case token(String)
    case answer(String)
    case toolCall(String, [String: Any])
    case error(String)
}

final class MojopiProcess: ObservableObject {
    let events = PassthroughSubject<MojopiEvent, Never>()
    private var process: Process?

    func send(prompt: String) {
        let projectRoot = findProjectRoot()
        let pixiBin = NSString(string: "~/.pixi/bin/pixi").expandingTildeInPath

        let shell = """
        PYTHONPATH=src mojo run -I src src/main.mojo -- \
          -p '\(prompt.replacingOccurrences(of: "'", with: "'\\''"))' \
          --mode json \
          --model mlx-community/gemma-4-e4b-it-4bit \
          --max-new-tokens 256
        """

        let task = Process()
        task.launchPath = pixiBin
        task.arguments = ["run", "bash", "-c", shell]
        task.currentDirectoryURL = URL(fileURLWithPath: projectRoot)

        let pipe = Pipe()
        task.standardOutput = pipe

        let handle = pipe.fileHandleForReading
        handle.readabilityHandler = { [weak self] h in
            let data = h.availableData
            guard !data.isEmpty, let str = String(data: data, encoding: .utf8) else { return }
            for line in str.split(separator: "\n", omittingEmptySubsequences: true) {
                self?.parseJSONLine(String(line))
            }
        }

        do {
            try task.run()
            self.process = task
            task.terminationHandler = { [weak self] _ in
                handle.readabilityHandler = nil
                DispatchQueue.main.async {
                    self?.events.send(.answer(""))  // signal completion
                }
            }
        } catch {
            events.send(.error("failed to spawn mojopi: \(error.localizedDescription)"))
        }
    }

    private func parseJSONLine(_ line: String) {
        let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("{") else { return }
        guard let data = trimmed.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }
        let type = json["type"] as? String ?? ""
        switch type {
        case "token":
            DispatchQueue.main.async { self.events.send(.token(json["text"] as? String ?? "")) }
        case "answer":
            DispatchQueue.main.async { self.events.send(.answer(json["text"] as? String ?? "")) }
        case "tool_call":
            DispatchQueue.main.async {
                self.events.send(.toolCall(
                    json["name"] as? String ?? "?",
                    json["arguments"] as? [String: Any] ?? [:]
                ))
            }
        case "error":
            DispatchQueue.main.async { self.events.send(.error(json["message"] as? String ?? "unknown")) }
        default:
            break
        }
    }

    private func findProjectRoot() -> String {
        var url = Bundle.main.bundleURL
        while url.path != "/" {
            if FileManager.default.fileExists(atPath: url.appendingPathComponent("pixi.toml").path) {
                return url.path
            }
            url.deleteLastPathComponent()
        }
        // Fallback: hard-coded dev path
        return NSString(string: "~/mojopi/mojopi").expandingTildeInPath
    }
}
