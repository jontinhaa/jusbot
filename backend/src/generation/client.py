"""Cliente Anthropic isolado. Carrega a chave do ambiente e expõe get_client()."""

import os

import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

_MODEL = "claude-sonnet-4-6"


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY não definida no .env")
    return anthropic.Anthropic(api_key=api_key)


def _test_connection() -> None:
    client = get_client()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=10,
        messages=[{"role": "user", "content": "responda só OK"}],
    )
    print(response.content[0].text)


if __name__ == "__main__":
    _test_connection()
