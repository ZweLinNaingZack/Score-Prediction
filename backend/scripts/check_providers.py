"""Try each AI provider that has a key in .env with one small prediction request.

    python -m scripts.check_providers

Costs a fraction of a cent per provider. If a model name is rejected it lists the names your key
can use, so you can set OPENAI_MODEL / XAI_MODEL / GEMINI_MODEL / ANTHROPIC_MODEL in .env.
"""
from app.config import settings
from app.llm.base import build_prompt
from app.llm.providers import PROVIDERS

KEYS = {
    "gpt": settings.openai_api_key,
    "grok": settings.xai_api_key,
    "gemini": settings.gemini_api_key,
    "claude": settings.anthropic_api_key,
}
MODELS = {
    "gpt": settings.openai_model,
    "grok": settings.xai_model,
    "gemini": settings.gemini_model,
    "claude": settings.anthropic_model,
}


def available_models(name: str) -> list[str]:
    if name in ("gpt", "grok"):
        from openai import OpenAI

        client = OpenAI(api_key=KEYS[name], **({"base_url": "https://api.x.ai/v1"} if name == "grok" else {}))
        return sorted(m.id for m in client.models.list())
    if name == "gemini":
        from google import genai

        client = genai.Client(api_key=KEYS[name])  # keep a reference: a dropped client closes its connection
        return sorted(m.name.removeprefix("models/") for m in client.models.list())
    import anthropic

    return sorted(m.id for m in anthropic.Anthropic(api_key=KEYS[name]).models.list())


def main() -> None:
    prompt = build_prompt("Arsenal", "Chelsea", "Premier League", "2026-11-01")
    for name, fn in PROVIDERS.items():
        if not KEYS[name]:
            print(f"{name:7} no key set, skipped")
            continue
        try:
            p = fn(prompt)
            print(f"{name:7} OK  model={MODELS[name]}  pick={p.home_goals}-{p.away_goals}  reason={p.reason[:70]!r}")
        except Exception as exc:
            print(f"{name:7} FAILED  model={MODELS[name]}: {str(exc)[:200]}")
            try:
                print("        models your key can use:", ", ".join(available_models(name))[:600])
            except Exception as exc2:
                print(f"        could not list models: {str(exc2)[:120]}")


if __name__ == "__main__":
    main()
