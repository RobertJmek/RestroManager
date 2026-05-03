"""Image processing utilities for menu item uploads.

Handles resizing, compression, and format conversion to optimize images for web delivery.
"""

import io
import base64
from PIL import Image, ImageOps
from typing import Tuple, Optional

# Configuration
MAX_DIMENSIONS = (800, 600)  # Max width x height for main image
THUMBNAIL_SIZE = (200, 200)  # For grid listings
TARGET_FORMAT = "WEBP"
TARGET_QUALITY = 85
MAX_FILE_SIZE_KB = 150


def process_image(
    image_bytes: bytes,
    filename: str,
    generate_thumbnail: bool = False
) -> Tuple[str, Optional[str]]:
    """
    Process uploaded image: resize, compress, convert to WebP base64.
    
    Args:
        image_bytes: Raw image data from upload
        filename: Original filename (for logging)
        generate_thumbnail: If True, also generate 200x200 thumbnail
    
    Returns:
        Tuple of (main_image_base64_url, thumbnail_base64_url or None)
        
    Raises:
        ValueError: If image is corrupted or processing fails
    """
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert RGBA to RGB if needed (WebP optimization)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize main image with aspect ratio preservation
        main_img = _resize_with_aspect_ratio(img, MAX_DIMENSIONS)
        
        # Optimize and convert to WebP
        main_webp_bytes = _optimize_for_size(main_img, TARGET_QUALITY, MAX_FILE_SIZE_KB)
        main_base64 = base64.b64encode(main_webp_bytes).decode()
        main_data_url = f"data:image/webp;base64,{main_base64}"
        
        # Generate thumbnail if requested
        thumbnail_data_url = None
        if generate_thumbnail:
            thumb_img = _resize_with_aspect_ratio(img, THUMBNAIL_SIZE)
            thumb_webp_bytes = _optimize_for_size(thumb_img, TARGET_QUALITY - 10, 50)
            thumb_base64 = base64.b64encode(thumb_webp_bytes).decode()
            thumbnail_data_url = f"data:image/webp;base64,{thumb_base64}"
        
        return main_data_url, thumbnail_data_url
        
    except Exception as e:
        raise ValueError(f"Image processing failed: {str(e)}")


def _resize_with_aspect_ratio(
    img: Image.Image, 
    max_size: Tuple[int, int]
) -> Image.Image:
    """
    Resize image to fit within max_size while preserving aspect ratio.
    
    Pads with white background if needed to match exact dimensions.
    
    Args:
        img: PIL Image object
        max_size: (width, height) tuple for max dimensions
    
    Returns:
        Resized PIL Image object
    """
    # Calculate scaling to fit within bounds
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Create new image with target size and white background
    new_img = Image.new('RGB', max_size, (255, 255, 255))
    
    # Paste original image centered
    offset = (
        (max_size[0] - img.width) // 2,
        (max_size[1] - img.height) // 2
    )
    new_img.paste(img, offset)
    
    return new_img


def _optimize_for_size(
    img: Image.Image,
    initial_quality: int = 85,
    target_kb: int = 150
) -> bytes:
    """
    Save image to WebP with iteratively reduced quality until target size reached.
    
    Args:
        img: PIL Image object
        initial_quality: Starting JPEG quality (0-100)
        target_kb: Target maximum file size in KB
    
    Returns:
        WEBP bytes data
    """
    quality = initial_quality
    
    while quality > 40:  # Don't go below 40% quality
        buffer = io.BytesIO()
        img.save(buffer, format=TARGET_FORMAT, quality=quality, method=6)
        file_size_kb = buffer.tell() / 1024
        
        if file_size_kb <= target_kb:
            buffer.seek(0)
            return buffer.read()
        
        quality -= 5
    
    # Fallback: return at lowest quality
    buffer = io.BytesIO()
    img.save(buffer, format=TARGET_FORMAT, quality=40, method=6)
    buffer.seek(0)
    return buffer.read()
