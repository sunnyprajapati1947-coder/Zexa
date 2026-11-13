"""Read-only discovery of optional Termux Android capabilities."""
from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class AndroidCapability:
    name: str
    command: str
    available: bool
    description: str


CAPABILITIES = (
    ("notification", "termux-notification", "Post an Android notification"),
    ("toast", "termux-toast", "Show a short Android toast"),
    ("clipboard_read", "termux-clipboard-get", "Read clipboard text"),
    ("clipboard_write", "termux-clipboard-set", "Write clipboard text"),
    ("speech_to_text", "termux-speech-to-text", "Capture speech as text"),
    ("text_to_speech", "termux-tts-speak", "Speak text aloud"),
    ("open_url", "termux-open-url", "Open a URL with an Android app"),
)


class AndroidCapabilityProbe:
    """Detect optional Termux commands; never invoke them."""

    def __init__(self, which=shutil.which):
        self._which = which

    def scan(self) -> list[AndroidCapability]:
        return [
            AndroidCapability(name, command, self._which(command) is not None, description)
            for name, command, description in CAPABILITIES
        ]

    def as_dict(self) -> dict:
        capabilities = self.scan()
        return {
            "platform": "android-termux",
            "mode": "read_only_detection",
            "actions_executed": False,
            "available_count": sum(item.available for item in capabilities),
            "capabilities": [
                {
                    "name": item.name,
                    "command": item.command,
                    "available": item.available,
                    "description": item.description,
                }
                for item in capabilities
            ],
        }


class TermuxAndroidHand:
    """Explicitly invoked, narrowly scoped Android notification adapter."""

    def __init__(self, which=shutil.which, run=None):
        import subprocess

        self._which = which
        self._run = run or subprocess.run

    def notify(self, title: str, content: str) -> None:
        import subprocess

        title = title.strip()
        content = content.strip()
        if not title or not content:
            raise ValueError("Notification title and content must not be empty.")
        if len(title) > 100 or len(content) > 1000:
            raise ValueError("Notification title/content exceeds the allowed length.")
        executable = self._which("termux-notification")
        if not executable:
            raise RuntimeError(
                "termux-notification is unavailable. Install Termux:API and its Termux package."
            )
        self._run(
            [executable, "--title", title, "--content", content],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )


    def set_torch(self, state: str) -> None:
        """Set the phone torch only for an explicit on/off request."""
        import subprocess

        state = state.strip().lower()
        if state not in {"on", "off"}:
            raise ValueError("Torch state must be 'on' or 'off'.")
        executable = self._which("termux-torch")
        if not executable:
            raise RuntimeError(
                "termux-torch is unavailable. Install Termux:API and the Android Termux:API app."
            )
        self._run(
            [executable, state],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )

class TermuxVoice:
    """Explicitly invoked Termux speech input/output adapter."""

    def __init__(self, which=shutil.which, run=None):
        import subprocess

        self._which = which
        self._run = run or subprocess.run

    def listen(self) -> str:
        executable = self._which("termux-speech-to-text")
        if not executable:
            raise RuntimeError("termux-speech-to-text is unavailable.")
        result = self._run(
            [executable],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        transcript = (result.stdout or "").strip()
        if not transcript:
            raise RuntimeError("No speech transcript was returned.")
        return transcript

    def speak(self, text: str) -> None:
        text = text.strip()
        if not text:
            raise ValueError("Speech text must not be empty.")
        if len(text) > 3000:
            raise ValueError("Speech text exceeds the 3000-character limit.")
        executable = self._which("termux-tts-speak")
        if not executable:
            raise RuntimeError("termux-tts-speak is unavailable.")
        self._run(
            [executable, text],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
