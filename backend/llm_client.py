"""
llm_client.py — Provider-agnostic LLM completion client.

Switch providers by setting LLM_PROVIDER env var:
  - openai    (default) → GPT-4o
  - anthropic           → Claude Haiku
  - ollama              → local Mistral/Llama via Ollama
"""

import os
from typing import Callable


def get_llm_client() -> Callable[[str, str], str]:
    """
    Return a completion function based on LLM_PROVIDER env var.

    Returns:
        Callable taking (system_prompt: str, user_prompt: str) → str response
    """
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        def complete(system_prompt: str, user_prompt: str) -> str:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content

        return complete

    elif provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        def complete(system_prompt: str, user_prompt: str) -> str:
            msg = client.messages.create(
                model="claude-haiku-20240307",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return msg.content[0].text

        return complete

    elif provider == "ollama":
        import requests
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "mistral")

        def complete(system_prompt: str, user_prompt: str) -> str:
            resp = requests.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
            )
            return resp.json()["message"]["content"]

        return complete

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. "
            "Supported values: openai, anthropic, ollama"
        )
