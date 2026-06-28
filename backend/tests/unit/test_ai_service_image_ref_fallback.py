import tempfile

from PIL import Image

from services.ai_service import AIService


class DummyTextProvider:
    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        return prompt


class DummyCaptionProvider:
    def generate_text(self, prompt: str, thinking_budget: int = 0) -> str:
        return prompt


class RefRejectingImageProvider:
    def __init__(self):
        self.calls = []

    def generate_image(
        self,
        prompt: str,
        ref_images=None,
        aspect_ratio: str = "16:9",
        resolution: str = "2K",
        enable_thinking: bool = False,
        thinking_budget: int = 0,
    ):
        self.calls.append(
            {
                "prompt": prompt,
                "ref_images": ref_images,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
            }
        )
        if ref_images:
            raise Exception("ClientError: 400 None. {'error': {'message': '***.data must be valid base64 image data'}}")
        return Image.new("RGB", (64, 64), color="green")


def test_generate_image_retries_without_reference_images():
    provider = RefRejectingImageProvider()
    service = AIService(
        text_provider=DummyTextProvider(),
        image_provider=provider,
        caption_provider=DummyCaptionProvider(),
    )

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        ref = Image.new("RGB", (32, 32), color="blue")
        ref.save(f, format="PNG")
        ref_path = f.name

    try:
        result = service.generate_image("test prompt", ref_image_path=ref_path)
    finally:
        import os
        os.unlink(ref_path)

    assert result is not None
    assert result.size == (64, 64)
    assert len(provider.calls) == 2
    assert provider.calls[0]["ref_images"] is not None
    assert provider.calls[1]["ref_images"] is None
