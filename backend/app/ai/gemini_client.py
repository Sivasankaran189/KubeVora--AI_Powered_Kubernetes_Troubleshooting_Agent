"""
KubeVora - Gemini API Client
Handles communication with Google Gemini API with timeouts, retries, and backoff.
"""
import json
import re
import time
from typing import Any, Dict, Optional
import httpx
from loguru import logger
from app.core.config import settings

GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
)


class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = settings.GEMINI_API_KEY if api_key is None else api_key
        self.model = settings.GEMINI_MODEL if model is None else model
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS if timeout is None else timeout
        self.max_retries = settings.GEMINI_MAX_RETRIES if max_retries is None else max_retries

    @staticmethod
    def clean_json_response(raw_text: str) -> str:
        """Strip markdown code fences from model response."""
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def generate_content(self, prompt: str) -> Dict[str, Any]:
        """Send prompt to Gemini API and parse structured JSON response."""
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured")
            return {
                "success": False,
                "error": "Gemini API key is not configured in environment variables",
                "data": None,
            }

        url = GEMINI_API_URL_TEMPLATE.format(model=self.model, key=self.api_key)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        headers = {"Content-Type": "application/json"}
        last_error = ""

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Calling Gemini API (model={self.model}, attempt={attempt + 1})")
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)

                # Success
                if resp.status_code == 200:
                    resp_json = resp.json()
                    candidates = resp_json.get("candidates", [])
                    if not candidates:
                        return {"success": False, "error": "No response candidates returned by Gemini", "data": None}

                    raw_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    cleaned = self.clean_json_response(raw_content)

                    try:
                        parsed_data = json.loads(cleaned)
                        return {"success": True, "data": parsed_data, "error": None}
                    except json.JSONDecodeError as jde:
                        logger.error(f"Failed to parse Gemini JSON output: {jde}")
                        return {"success": False, "error": f"Invalid JSON output from AI: {jde}", "data": None}

                # Rate Limit / Quota Exceeded (429) or Server Error (503) -> Retry with backoff
                elif resp.status_code in (429, 503):
                    last_error = f"Gemini API returned status {resp.status_code}: {resp.text[:150]}"
                    if attempt < self.max_retries:
                        sleep_time = (2 ** attempt) * 1.5
                        logger.warning(f"Gemini API {resp.status_code}, retrying in {sleep_time}s...")
                        time.sleep(sleep_time)
                        continue
                else:
                    # Non-retryable error (e.g. 400 Bad Request, 401 Invalid Key)
                    logger.error(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
                    return {
                        "success": False,
                        "error": f"Gemini API returned HTTP {resp.status_code}",
                        "data": None,
                    }

            except httpx.TimeoutException:
                last_error = f"Gemini request timed out after {self.timeout}s"
                if attempt < self.max_retries:
                    time.sleep(1.0)
                    continue
            except Exception as e:
                logger.error(f"Unexpected error calling Gemini API: {e}")
                return {"success": False, "error": str(e), "data": None}

        return {"success": False, "error": last_error or "Exceeded maximum retries", "data": None}


gemini_client = GeminiClient()
