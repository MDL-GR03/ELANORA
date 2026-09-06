import io

import pytest
from PIL import Image

from app.service.instance_assets import normalize_logo


def test_logo_is_normalized_to_bounded_metadata_free_webp() -> None:
    source = io.BytesIO()
    image = Image.new("RGB", (900, 300), "#234e70")
    exif = Image.Exif()
    exif[0x010E] = "private description"
    image.save(source, format="JPEG", exif=exif)

    content, width, height = normalize_logo(source.getvalue())

    assert (width, height) == (512, 171)
    with Image.open(io.BytesIO(content)) as normalized:
        assert normalized.format == "WEBP"
        assert normalized.size == (512, 512)
        assert not normalized.getexif()


@pytest.mark.parametrize("content", [b"not an image", b""])
def test_logo_rejects_invalid_content(content: bytes) -> None:
    with pytest.raises(ValueError, match="Logo must"):
        normalize_logo(content)
