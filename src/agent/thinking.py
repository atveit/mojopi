"""Strip reasoning-model thinking blocks from generated text.

Supports multiple thinking tag conventions:
  <think>...</think>         (DeepSeek-R1, QwQ, Qwen3-Thinking)
  <thinking>...</thinking>    (Claude-style, alternative)
  <|thinking|>...<|/thinking|>  (some instruction-tuned models)

Also strips common code-fence-wrapped reasoning that looks like:
  ```thinking
  ...
  ```

The thinking content is returned separately so it can be logged for debug.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

# Order matters: try the most specific pattern first.
_PATTERNS = [
    re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<thinking>(.*?)</thinking>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<\|thinking\|>(.*?)<\|/thinking\|>", re.DOTALL | re.IGNORECASE),
    re.compile(r"```thinking\n(.*?)```", re.DOTALL | re.IGNORECASE),
]


@dataclass
class StrippedText:
    visible: str
    thinking: str

    def has_thinking(self) -> bool:
        return bool(self.thinking)


def strip_thinking(text: str) -> StrippedText:
    """Return (visible_text, thinking_text).

    The thinking blocks are concatenated with double newlines; the visible
    text has them removed and any leftover double blank lines collapsed.
    """
    if not text:
        return StrippedText(visible="", thinking="")

    thinking_parts: list[str] = []
    visible = text

    for pattern in _PATTERNS:
        def _capture(m):
            thinking_parts.append(m.group(1).strip())
            return ""
        visible = pattern.sub(_capture, visible)

    # Handle unclosed <think> — strip everything from <think> to end.
    m = re.search(r"<think>(.*)", visible, re.DOTALL | re.IGNORECASE)
    if m:
        thinking_parts.append(m.group(1).strip())
        visible = visible[:m.start()]

    # Collapse 3+ newlines left by stripping into 2.
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()

    return StrippedText(
        visible=visible,
        thinking="\n\n".join(t for t in thinking_parts if t),
    )


def strip_thinking_text(text: str) -> str:
    """Convenience: return only the visible text."""
    return strip_thinking(text).visible


def has_thinking_block(text: str) -> bool:
    """Fast probe — does this text contain any supported thinking tag?"""
    if not text:
        return False
    return any(p.search(text) for p in _PATTERNS) or "<think>" in text.lower()
