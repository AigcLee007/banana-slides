from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from services.ai_providers.image.genai_provider import GenAIImageProvider


def test_reference_images_are_encoded_as_genai_parts():
    captured = {}

    def fake_generate_content(*, model, contents, config):
        captured["model"] = model
        captured["contents"] = contents
        captured["config"] = config
        return SimpleNamespace(parts=[])

    fake_client = SimpleNamespace(
        models=SimpleNamespace(generate_content=fake_generate_content)
    )

    with patch(
        "services.ai_providers.image.genai_provider.make_genai_client",
        return_value=fake_client,
    ):
        provider = GenAIImageProvider(model="gemini-3-pro-image-preview", api_key="test")

    ref = Image.new("RGB", (32, 32), color="blue")

    try:
        provider.generate_image("test prompt", ref_images=[ref], enable_thinking=False)
    except Exception:
        # Response is intentionally incomplete; we only care about request construction.
        pass

    assert len(captured["contents"]) == 2
    ref_part = captured["contents"][0]
    assert not isinstance(ref_part, Image.Image)
    assert hasattr(ref_part, "inline_data")
    assert getattr(ref_part.inline_data, "data", None)
    assert getattr(ref_part.inline_data, "mime_type", None) in {"image/jpeg", "image/png"}
    assert captured["contents"][1] == "test prompt"
