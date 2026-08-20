"""Synthetic unit tests for receipt-image safety and normalization."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

import checkmate.adapters.receipt_parser as receipt_adapter
from checkmate.adapters.receipt_parser import PillowReceiptImageNormalizer
from checkmate.application.extraction import ReceiptExtractionError


def make_image(
    image_format: str,
    *,
    size: tuple[int, int] = (80, 40),
    mode: str = "RGB",
    exif: Image.Exif | None = None,
    comment: bytes | None = None,
) -> bytes:
    """Create one fully synthetic encoded image."""
    color: int | tuple[int, ...] = 160 if mode == "L" else (20, 120, 180)
    if mode == "RGBA":
        color = (20, 120, 180, 100)
    image = Image.new(mode, size, color)
    output = BytesIO()
    options: dict[str, object] = {}
    if exif is not None:
        options["exif"] = exif
    if comment is not None:
        options["comment"] = comment
    image.save(output, format=image_format, **options)
    return output.getvalue()


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_supported_formats_become_metadata_free_jpegs(image_format: str) -> None:
    normalizer = PillowReceiptImageNormalizer()

    result = normalizer.normalize(make_image(image_format))

    assert result.media_type == "image/jpeg"
    assert result.width == 80
    assert result.height == 40
    with Image.open(BytesIO(result.content)) as normalized:
        normalized.load()
        assert normalized.format == "JPEG"
        assert normalized.mode == "RGB"
        assert normalized.getexif() == {}
        assert "comment" not in normalized.info


def test_invalid_bytes_and_known_unsupported_formats_have_distinct_errors() -> None:
    normalizer = PillowReceiptImageNormalizer()

    with pytest.raises(ReceiptExtractionError) as invalid:
        normalizer.normalize(b"not an image")
    with pytest.raises(ReceiptExtractionError) as unsupported:
        normalizer.normalize(b"GIF89a" + b"synthetic")

    assert invalid.value.code == "invalid_receipt_image"
    assert unsupported.value.code == "unsupported_receipt_format"


def test_multiframe_supported_image_is_rejected() -> None:
    first = Image.new("RGB", (20, 20), "white")
    second = Image.new("RGB", (20, 20), "black")
    output = BytesIO()
    first.save(output, format="PNG", save_all=True, append_images=[second])

    with pytest.raises(ReceiptExtractionError) as raised:
        PillowReceiptImageNormalizer().normalize(output.getvalue())

    assert raised.value.code == "animated_receipt_not_supported"


def test_pixel_limit_and_decompression_warnings_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = make_image("PNG", size=(10, 10))
    monkeypatch.setattr(receipt_adapter, "MAX_IMAGE_PIXELS", 99)
    with pytest.raises(ReceiptExtractionError) as pixel_error:
        PillowReceiptImageNormalizer().normalize(content)
    assert pixel_error.value.category == "too_many_pixels"

    monkeypatch.setattr(receipt_adapter, "MAX_IMAGE_PIXELS", 25_000_000)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 80)
    with pytest.raises(ReceiptExtractionError) as warning_error:
        PillowReceiptImageNormalizer().normalize(content)
    assert warning_error.value.category == "decompression_bomb"


def test_exif_orientation_is_applied_and_source_metadata_is_removed() -> None:
    exif = Image.Exif()
    exif[274] = 6
    content = make_image(
        "JPEG",
        size=(40, 20),
        exif=exif,
        comment=b"synthetic private metadata",
    )

    result = PillowReceiptImageNormalizer().normalize(content)

    assert (result.width, result.height) == (20, 40)
    with Image.open(BytesIO(result.content)) as normalized:
        assert normalized.getexif() == {}
        assert b"synthetic private metadata" not in result.content


def test_color_conversion_downscales_without_upscaling() -> None:
    normalizer = PillowReceiptImageNormalizer()

    downscaled = normalizer.normalize(make_image("PNG", size=(5_000, 10), mode="RGBA"))
    unchanged = normalizer.normalize(make_image("PNG", size=(400, 200), mode="L"))

    assert (downscaled.width, downscaled.height) == (4_000, 8)
    assert (unchanged.width, unchanged.height) == (400, 200)
    with Image.open(BytesIO(downscaled.content)) as normalized:
        assert normalized.mode == "RGB"


def test_normalization_uses_the_approved_jpeg_quality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_save = Image.Image.save
    observed_quality: list[int] = []

    def recording_save(
        self: Image.Image, fp: object, format: str, **params: object
    ) -> None:
        if format == "JPEG" and "quality" in params:
            observed_quality.append(int(params["quality"]))
        original_save(self, fp, format=format, **params)

    monkeypatch.setattr(Image.Image, "save", recording_save)

    PillowReceiptImageNormalizer().normalize(make_image("PNG"))

    assert observed_quality[-1] == 90
