# mojopi-mac — Native SwiftUI app

A minimal SwiftUI chat UI for mojopi on macOS 14+.

## Build

```bash
cd apps/mojopi-mac
swift build -c release
```

Binary is at `.build/release/mojopi-mac`. (This is a Swift Package
executable, not a .app bundle — wrap it in an .app with `swiftpackage
--product mojopi-mac` or hand-bundle it later.)

## Run (dev)

```bash
swift run mojopi-mac
```

## Architecture

- `mojopi_macApp.swift` — SwiftUI App entry, menu commands (⌘N new session, ⌘K clear)
- `ContentView.swift` — chat pane + input field + message rendering
- `MojopiProcess.swift` — spawns `mojopi --mode json` as subprocess,
  parses JSONL events (`token`, `tool_call`, `answer`, `error`) and
  publishes them via Combine

## Status

v1.3 — built + swift build verified. Tool-call rendering is a single
"[calling tool…]" line; richer UI lives in v1.4.
