import SwiftUI

struct Message: Identifiable {
    let id = UUID()
    let role: String
    var content: String
}

struct ContentView: View {
    @State private var messages: [Message] = []
    @State private var inputText: String = ""
    @State private var isGenerating: Bool = false
    @State private var currentAssistantId: UUID? = nil
    @StateObject private var process = MojopiProcess()

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        ForEach(messages) { msg in
                            MessageView(message: msg)
                                .id(msg.id)
                        }
                    }
                    .padding()
                }
                .onChange(of: messages.last?.id) { _ in
                    if let id = messages.last?.id {
                        withAnimation { proxy.scrollTo(id, anchor: .bottom) }
                    }
                }
            }
            Divider()
            HStack(alignment: .bottom, spacing: 8) {
                TextField("Ask mojopi…", text: $inputText, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit(sendPrompt)
                Button(action: sendPrompt) {
                    Image(systemName: isGenerating ? "stop.circle" : "paperplane.fill")
                }
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(inputText.isEmpty && !isGenerating)
            }
            .padding()
        }
        .background(.background)
        .onReceive(NotificationCenter.default.publisher(for: .newSession)) { _ in
            messages.removeAll()
        }
        .onReceive(NotificationCenter.default.publisher(for: .clearSession)) { _ in
            messages.removeAll()
        }
        .onReceive(process.events) { event in
            handle(event)
        }
    }

    private func sendPrompt() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        inputText = ""
        messages.append(Message(role: "user", content: text))
        let assistantMsg = Message(role: "assistant", content: "")
        messages.append(assistantMsg)
        currentAssistantId = assistantMsg.id
        isGenerating = true
        process.send(prompt: text)
    }

    private func handle(_ event: MojopiEvent) {
        switch event {
        case .token(let text):
            if let id = currentAssistantId,
               let idx = messages.firstIndex(where: { $0.id == id }) {
                messages[idx].content += text
            }
        case .answer(let text):
            if let id = currentAssistantId,
               let idx = messages.firstIndex(where: { $0.id == id }) {
                messages[idx].content = text
            }
            isGenerating = false
            currentAssistantId = nil
        case .toolCall(let name, _):
            if let id = currentAssistantId,
               let idx = messages.firstIndex(where: { $0.id == id }) {
                messages[idx].content += "\n\n[calling \(name)…]"
            }
        case .error(let msg):
            if let id = currentAssistantId,
               let idx = messages.firstIndex(where: { $0.id == id }) {
                messages[idx].content += "\n\n[error: \(msg)]"
            }
            isGenerating = false
            currentAssistantId = nil
        }
    }
}

struct MessageView: View {
    let message: Message

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Text(message.role == "user" ? "👤" : "🤖")
                .font(.title2)
            VStack(alignment: .leading, spacing: 4) {
                Text(message.role.capitalized)
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)
                Text(message.content)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}
