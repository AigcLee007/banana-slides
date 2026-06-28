"""Google GenAI image provider using direct REST calls.

This implementation avoids the SDK's multipart encoding path so it can work
with OpenAI/Gemini-compatible proxies that expect explicit REST JSON payloads
with base64 inline image data.
"""
import base64
import logging
from io import BytesIO
from typing import List, Optional

import requests
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_config
from .base import ImageProvider

logger = logging.getLogger(__name__)


def _image_to_inline_data(image: Image.Image) -> dict:
    """Convert a PIL image to Gemini REST inline_data JSON."""
    buffer = BytesIO()
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        image.save(buffer, format="PNG")
        mime_type = "image/png"
    else:
        image = image.convert("RGB")
        image.save(buffer, format="JPEG", quality=95)
        mime_type = "image/jpeg"
    return {
        "mime_type": mime_type,
        "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
    }


def _get_first_present(mapping: dict, *keys):
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _decode_inline_data(part: dict) -> Optional[Image.Image]:
    inline_data = _get_first_present(part, "inline_data", "inlineData")
    if not isinstance(inline_data, dict):
        return None
    data = _get_first_present(inline_data, "data")
    if not data:
        return None
    return Image.open(BytesIO(base64.b64decode(data)))


class GenAIImageProvider(ImageProvider):
    """Image generation via Gemini REST API."""

    def __init__(
        self,
        model: str = "gemini-3-pro-image-preview",
        api_key: str = None,
        api_base: str = None,
        vertexai: bool = False,
        project_id: str = None,
        location: str = None,
    ):
        self.model = model
        self.api_key = api_key or ""
        self.api_base = (api_base or "").rstrip("/")
        self.vertexai = vertexai
        self.project_id = project_id
        self.location = location

    def _build_url(self) -> str:
        if self.vertexai:
            project = self.project_id or ""
            location = self.location or "us-central1"
            return (
                "https://generativelanguage.googleapis.com"
                f"/v1beta/projects/{project}/locations/{location}/publishers/google/models/"
                f"{self.model}:generateContent"
            )
        base = self.api_base or "https://generativelanguage.googleapis.com"
        return f"{base}/v1beta/models/{self.model}:generateContent"

    def _build_headers(self) -> dict:
        if self.vertexai:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _build_payload(
        self,
        prompt: str,
        ref_images: Optional[List[Image.Image]] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = True,
        thinking_budget: int = 1024,
    ) -> dict:
        parts = []
        if ref_images:
            for ref_img in ref_images:
                inline_data = _image_to_inline_data(ref_img)
                parts.append({
                    "inline_data": inline_data,
                    "inlineData": {
                        "mimeType": inline_data["mime_type"],
                        "data": inline_data["data"],
                    },
                })
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": resolution,
                },
                "image_config": {
                    "aspect_ratio": aspect_ratio,
                    "image_size": resolution,
                },
            },
        }
        if enable_thinking:
            payload["generationConfig"]["thinkingConfig"] = {
                "thinkingBudget": thinking_budget,
                "includeThoughts": True,
            }
            payload["generationConfig"]["thinking_config"] = {
                "thinking_budget": thinking_budget,
                "include_thoughts": True,
            }
        return payload

    def _extract_image_from_response(self, response) -> Image.Image:
        """Extract the last image from a Gemini REST response."""
        if isinstance(response, dict):
            candidates = response.get("candidates") or response.get("data") or []
            for candidate in reversed(candidates):
                if isinstance(candidate, dict):
                    content = candidate.get("content") or candidate.get("message") or candidate
                    if isinstance(content, dict):
                        parts = content.get("parts") or content.get("images") or []
                    else:
                        parts = []
                else:
                    parts = []
                for part in reversed(parts):
                    if not isinstance(part, dict):
                        continue
                    image = _decode_inline_data(part)
                    if image:
                        return image
                    b64 = _get_first_present(part, "b64_json", "b64Json")
                    if b64:
                        return Image.open(BytesIO(base64.b64decode(b64)))
                    url = _get_first_present(part, "url", "image_url")
                    if isinstance(url, dict):
                        url = url.get("url")
                    if url:
                        resp = requests.get(url, timeout=60, stream=True)
                        resp.raise_for_status()
                        return Image.open(BytesIO(resp.content))

            data = response.get("data") or response.get("candidates") or []
            for item in reversed(data):
                if isinstance(item, dict):
                    image = _decode_inline_data(item)
                    if image:
                        return image
                    b64 = _get_first_present(item, "b64_json", "b64Json")
                    if b64:
                        return Image.open(BytesIO(base64.b64decode(b64)))
                    url = _get_first_present(item, "url")
                    if url:
                        resp = requests.get(url, timeout=60, stream=True)
                        resp.raise_for_status()
                        return Image.open(BytesIO(resp.content))

        raise ValueError(f"No image found in API response. type={type(response).__name__}")

    @retry(
        stop=stop_after_attempt(get_config().GENAI_MAX_RETRIES + 1),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_image(
        self,
        prompt: str,
        ref_images: Optional[List[Image.Image]] = None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = True,
        thinking_budget: int = 1024,
    ) -> Optional[Image.Image]:
        try:
            url = self._build_url()
            headers = self._build_headers()
            payload = self._build_payload(
                prompt=prompt,
                ref_images=ref_images,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                enable_thinking=enable_thinking,
                thinking_budget=thinking_budget,
            )

            logger.warning(
                "GenAI REST image request: url=%s refs=%d model=%s",
                url,
                len(ref_images) if ref_images else 0,
                self.model,
            )
            response = requests.post(url, headers=headers, json=payload, timeout=get_config().GENAI_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            return self._extract_image_from_response(data)
        except Exception as e:
            error_detail = f"Error generating image with GenAI REST: {type(e).__name__}: {str(e)}"
            logger.error(error_detail, exc_info=True)
            raise Exception(error_detail) from e
