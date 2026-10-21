from __future__ import annotations

import json


class LLMError(RuntimeError):
    pass


class GroqAnswerer:
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-20b"):
        if not api_key:
            raise LLMError("A Groq API key is required.")
        try:
            from groq import Groq
        except ImportError as exc:
            raise LLMError(
                "The Groq SDK is not installed. Run: python -m pip install -r requirements.txt"
            ) from exc
        self.client = Groq(api_key=api_key)
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            raise LLMError(f"Groq request failed: {exc}") from exc
        if not response.choices or not response.choices[0].message.content:
            raise LLMError("Groq returned an empty answer.")
        return response.choices[0].message.content.strip()
