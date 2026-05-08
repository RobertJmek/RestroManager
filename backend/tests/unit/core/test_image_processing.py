import pytest
from PIL import Image
import io
import base64

from core.image_processing import process_image

def create_test_image_bytes(width=100, height=100, color="red"):
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_process_image_success():
    img_bytes = create_test_image_bytes(1000, 1000)
    main_url, thumb_url = process_image(img_bytes, "test.jpg", generate_thumbnail=True)
    
    assert main_url.startswith("data:image/webp;base64,")
    assert thumb_url.startswith("data:image/webp;base64,")
    
    # decode main to verify
    main_bytes = base64.b64decode(main_url.split(",")[1])
    main_img = Image.open(io.BytesIO(main_bytes))
    
    assert main_img.format == "WEBP"
    assert main_img.size == (800, 600)  # should match MAX_DIMENSIONS

def test_process_image_no_thumbnail():
    img_bytes = create_test_image_bytes(500, 500)
    main_url, thumb_url = process_image(img_bytes, "test.jpg", generate_thumbnail=False)
    
    assert main_url.startswith("data:image/webp;base64,")
    assert thumb_url is None

def test_process_image_invalid_bytes():
    with pytest.raises(ValueError) as exc_info:
        process_image(b"invalid image bytes", "test.jpg")
    
    assert "Image processing failed" in str(exc_info.value)
