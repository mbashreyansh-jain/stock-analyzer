"""Google Gemini, used for the few features that write text (D23). The API key never leaves the server.

If no key is set, or Gemini is unavailable, callers fall back to the free templates.
"""

import json

import httpx

from stockai.config import Settings, get_settings

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class AIError(Exception):
    """code is one the pages already understand: not_granted, rate_limited, invalid_json, refused, upstream_error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _parse_json(text: str):
    """The whole answer as JSON, or else the part from the first { or [ to the last } or ]."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
        end = max(text.rfind("}"), text.rfind("]"))
        if starts and end > min(starts):
            try:
                return json.loads(text[min(starts):end + 1])
            except json.JSONDecodeError:
                pass
    raise AIError("invalid_json", "Gemini's answer wasn't in the expected format. Try again.")


def generate_json(prompt: str, settings: Settings | None = None, client: httpx.Client | None = None):
    s = settings or get_settings()
    if not s.gemini_api_key:
        raise AIError("not_granted", "No Gemini API key is set on the server (GEMINI_API_KEY in .env).")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }
    http = client or httpx.Client(timeout=120)
    try:
        r = http.post(URL.format(model=s.gemini_model), headers={"x-goog-api-key": s.gemini_api_key}, json=body)
    except httpx.HTTPError as exc:
        raise AIError("upstream_error", "Couldn't reach Gemini. Check the internet connection.") from exc
    finally:
        if client is None:
            http.close()
    if r.status_code == 429:
        raise AIError("rate_limited", "Gemini's limit for now is used up. Try again later.")
    if r.status_code in (401, 403):
        raise AIError("not_granted", "Gemini refused the API key. Check GEMINI_API_KEY in .env.")
    if r.status_code == 404:
        raise AIError("upstream_error", f"Gemini has no model called '{s.gemini_model}'. Set GEMINI_MODEL in .env.")
    if r.status_code >= 400:
        raise AIError("upstream_error", f"Gemini returned an error ({r.status_code}).")
    data = r.json()
    candidates = data.get("candidates") or []
    text = "".join(p.get("text", "") for p in (candidates[0].get("content", {}).get("parts", []) if candidates else []))
    if not text.strip():
        raise AIError("refused", "Gemini didn't write an answer for this request.")
    return _parse_json(text)
