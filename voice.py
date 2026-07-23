"""Voice input and text-to-speech for Jarvis."""

from __future__ import annotations

import threading
from typing import Callable

import pyttsx3

try:
    import speech_recognition as sr

    VOICE_INPUT_AVAILABLE = True
except ImportError:
    sr = None  # type: ignore[assignment]
    VOICE_INPUT_AVAILABLE = False


class VoiceEngine:
    """Handles microphone capture and spoken responses."""

    def __init__(self) -> None:
        self._recognizer = sr.Recognizer() if VOICE_INPUT_AVAILABLE else None
        self._tts = pyttsx3.init()
        self._tts.setProperty("rate", 175)
        self._speaking = False
        self._microphone_available = self._detect_microphone()

    def _detect_microphone(self) -> bool:
        if not VOICE_INPUT_AVAILABLE or self._recognizer is None:
            return False
        try:
            with sr.Microphone():
                return True
        except (OSError, AttributeError):
            return False

    @property
    def microphone_available(self) -> bool:
        return self._microphone_available

    def listen(self, timeout: int = 5, phrase_limit: int = 8) -> tuple[str | None, str | None]:
        """
        Capture speech from the default microphone.

        Returns (transcript, error_message).
        """
        if not self._microphone_available or self._recognizer is None:
            return (
                None,
                "Voice input is unavailable. Install PyAudio for microphone support, "
                "or type your message instead.",
            )

        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
        except sr.WaitTimeoutError:
            return None, "I did not hear anything. Try again."
        except OSError as exc:
            return None, f"Microphone unavailable: {exc}"

        try:
            text = self._recognizer.recognize_google(audio)
            return text.strip(), None
        except sr.UnknownValueError:
            return None, "I could not understand that. Please repeat."
        except sr.RequestError as exc:
            return None, f"Speech recognition failed: {exc}"

    def speak(self, text: str, on_done: Callable[[], None] | None = None) -> None:
        """Speak text asynchronously so the UI stays responsive."""
        if not text.strip():
            if on_done:
                on_done()
            return

        def _run() -> None:
            self._speaking = True
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            finally:
                self._speaking = False
                if on_done:
                    on_done()

        threading.Thread(target=_run, daemon=True).start()

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self) -> None:
        try:
            self._tts.stop()
        except RuntimeError:
            pass
