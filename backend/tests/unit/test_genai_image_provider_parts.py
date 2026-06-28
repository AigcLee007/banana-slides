import base64
from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image

from services.ai_providers.image.genai_provider import GenAIImageProvider


def _make_png_b64(color="blue"):
    img = Image.new("RGB", (16, 16), color=color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _make_provider():
    return GenAIImageProvider(model="gemini-3-pro-image-preview", api_key="test", api_base="http://test")


def test_generate_image_sends_inline_data_request():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inline_data": {
                                    "mime_type": "image/png",
                                    "data": _make_png_b64("red"),
                                }
                            }
                        ]
                    }
                }
            ]
        }
        return resp

    ref = Image.new("RGB", (32, 32), color="blue")
    provider = _make_provider()

    with patch("services.ai_providers.image.genai_provider.requests.post", side_effect=fake_post):
        image = provider.generate_image("test prompt", ref_images=[ref], enable_thinking=False)

    assert isinstance(image, Image.Image)
    assert captured["url"].endswith("/v1beta/models/gemini-3-pro-image-preview:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "test"
    ref_part = captured["json"]["contents"][0]["parts"][0]
    assert "inline_data" in ref_part
    assert ref_part["inline_data"]["data"]
    assert ref_part["inline_data"]["mime_type"] in {"image/jpeg", "image/png"}
    assert captured["json"]["contents"][0]["parts"][1]["text"] == "test prompt"


def test_extract_image_from_rest_response_inline_data():
    provider = _make_provider()
    response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "draft"},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": _make_png_b64("green"),
                            }
                        },
                    ]
                }
            }
        ]
    }

    image = provider._extract_image_from_response(response)
    assert isinstance(image, Image.Image)


def test_extract_image_from_rest_response_accepts_fallback_shapes():
    provider = _make_provider()
    response = {
        "data": [
            {
                "message": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": _make_png_b64("purple"),
                            }
                        }
                    ]
                }
            }
        ]
    }

    image = provider._extract_image_from_response(response)
    assert isinstance(image, Image.Image)
