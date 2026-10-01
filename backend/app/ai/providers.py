from typing import Protocol


class LLMProvider(Protocol):
    def generate(self, system_prompt: str, user_message: str) -> str: ...


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio: bytes, language: str | None = None) -> str: ...


class TextToSpeechProvider(Protocol):
    def synthesize(self, text: str, language: str) -> bytes: ...


class VoiceProvider(Protocol):
    def answer_call(self, call_id: str) -> None: ...

    def transfer_call(self, call_id: str, destination: str) -> None: ...


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class UnconfiguredProvider:
    def __getattr__(self, name: str):
        raise RuntimeError("No production AI or voice provider is configured")
