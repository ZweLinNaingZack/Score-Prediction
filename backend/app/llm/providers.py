"""One function per AI provider. Each returns a Prediction."""
import json
import time

from app.config import settings
from app.llm.base import Prediction


def _retry(call, attempts: int = 4):
    """Overloaded (503) and rate-limited (429) replies are common on free tiers: wait and try again."""
    for i in range(attempts):
        try:
            return call()
        except Exception as exc:
            busy = any(code in str(exc) for code in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"))
            if not busy or i == attempts - 1:
                raise
            time.sleep(5 * (i + 1))


def _parse(text: str) -> Prediction:
    start, end = text.find("{"), text.rfind("}") + 1
    return Prediction(**json.loads(text[start:end]))


def predict_gpt(prompt: str) -> Prediction:
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    r = client.chat.completions.create(model=settings.openai_model, messages=[{"role": "user", "content": prompt}])
    return _parse(r.choices[0].message.content)


def predict_grok(prompt: str) -> Prediction:
    from openai import OpenAI
    client = OpenAI(api_key=settings.xai_api_key, base_url="https://api.x.ai/v1")
    r = client.chat.completions.create(model=settings.xai_model, messages=[{"role": "user", "content": prompt}])
    return _parse(r.choices[0].message.content)


def predict_gemini(prompt: str) -> Prediction:
    from google import genai
    client = genai.Client(api_key=settings.gemini_api_key)
    r = _retry(lambda: client.models.generate_content(model=settings.gemini_model, contents=prompt))
    return _parse(r.text)


def predict_claude(prompt: str) -> Prediction:
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    r = client.messages.create(model=settings.anthropic_model, max_tokens=400, messages=[{"role": "user", "content": prompt}])
    return _parse(r.content[0].text)


PROVIDERS = {"gpt": predict_gpt, "grok": predict_grok, "gemini": predict_gemini, "claude": predict_claude}
