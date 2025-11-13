# app/services/replicate_client.py
import os
import time
import random
import requests
from typing import Optional

# Read key from environment for safety
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyATdX-0CN2CMfJWkhVVju11ahdKmTwZxxM").strip()
MODEL = "gemini-2.5-flash"

class ReplicateError(Exception):
    pass

def _extract_text_from_response(data: dict) -> Optional[str]:
    """
    Try several common patterns returned by the Gemini REST API and return
    the first non-empty string found. Return None if nothing useful found.
    """
    if not isinstance(data, dict):
        return None

    # Common: data["candidates"][0]["content"]["parts"][0]["text"]
    try:
        candidates = data.get("candidates")
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            content = first.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list) and parts:
                    text = parts[0].get("text")
                    if isinstance(text, str) and text.strip():
                        return text.strip()
    except Exception:
        pass

    # Some responses embed output under different keys
    for key in ("output", "result", "message"):
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, dict):
            for subkey in ("text", "content", "message"):
                if subkey in val and isinstance(val[subkey], str) and val[subkey].strip():
                    return val[subkey].strip()

    # Fallback: try to stringify candidate area
    try:
        if "candidates" in data:
            return str(data["candidates"])
    except Exception:
        pass

    return None


def call_replicate(prompt: str, timeout: int = 120) -> str:
    """
    Send prompt to Gemini 2.5 Flash with robust retry/backoff and return text.
    Raises ReplicateError on fatal issues (missing key, quota, persistent overload, etc).
    """

    if not GEMINI_API_KEY:
        raise ReplicateError(
            "Gemini API key not found. Set environment variable GEMINI_API_KEY before running."
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI_API_KEY}"

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    max_retries = 8
    base_delay = 1.5  # base for exponential backoff
    start_time = time.time()

    last_response_text = None
    for attempt in range(max_retries):
        # Respect overall timeout
        if time.time() - start_time > timeout:
            raise ReplicateError("Request timed out while waiting for Gemini (overall timeout).")

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.RequestException as e:
            # network-level problem — retry a few times
            if attempt < max_retries - 1:
                sleep_for = base_delay * (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_for)
                continue
            raise ReplicateError(f"Network error contacting Gemini: {e}")

        status = resp.status_code
        text_body = resp.text or ""
        last_response_text = text_body

        # 503 -> overloaded: retry with backoff + jitter
        if status == 503:
            if attempt < max_retries - 1:
                sleep_for = base_delay * (2 ** attempt) + random.uniform(0, 1)
                # small log on server console (not required)
                print(f"[Gemini] 503 Overloaded. Backing off {sleep_for:.1f}s (attempt {attempt+1}/{max_retries})")
                time.sleep(sleep_for)
                continue
            raise ReplicateError("Gemini API still overloaded after retries (503).")

        # 429 -> quota exhausted: stop and tell user
        if status == 429:
            raise ReplicateError(
                "Gemini API quota exceeded (429). Check billing/usage or use a different key."
            )

        # Other client/server errors -> fail fast
        if status >= 400:
            raise ReplicateError(f"Gemini API returned {status}: {text_body}")

        # success -> try to parse JSON
        try:
            data = resp.json()
        except Exception:
            # If not JSON, return raw text if non-empty
            if text_body.strip():
                return text_body.strip()
            raise ReplicateError("Gemini returned non-JSON empty response.")

        # extract text
        extracted = _extract_text_from_response(data)
        if extracted and extracted.strip():
            return extracted.strip()

        # If extraction failed but resp included something, try a last-ditch string
        if isinstance(data, dict) and data:
            # return stringified data as fallback
            return str(data)

        # If nothing useful, retry (rare)
        if attempt < max_retries - 1:
            sleep_for = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(sleep_for)
            continue

    # If we exit loop without a good reply
    raise ReplicateError(
        "No usable text returned from Gemini. Last response: "
        + (last_response_text[:1000] if last_response_text else "<empty>")
    )
