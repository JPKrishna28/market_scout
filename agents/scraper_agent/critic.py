import json
from llm.nvidia_client import invoke_llm


def is_technical(text: str) -> bool:
    prompt = f"""
Determine if this content contains REAL technical updates
(APIs, SDKs, infra, models, releases).

Respond ONLY in valid JSON:
{{ "technical": true or false }}

Text:
{text[:1200]}
"""

    raw_response = invoke_llm(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=50,
    )

    # 🔥 Handle string safely
    if isinstance(raw_response, str):
        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError:
            return False
    elif isinstance(raw_response, dict):
        parsed = raw_response
    else:
        return False

    return parsed.get("technical", False)