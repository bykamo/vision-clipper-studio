#!/usr/bin/env python3
"""Generate logo variants and favicon from the new master logo.

Input:  frontend/public/images/logo.png (1254x1254, RGB, dark bg)
Output: all variants in frontend/public/images/ and frontend/public/favicon.*
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)


def remove_black_bg(img: Image.Image, threshold: int = 30) -> Image.Image:
    """Convert near-black pixels to transparent.
    
    Works for logos on dark/black backgrounds. Pixels where all RGB channels
    are below `threshold` become fully transparent.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        # If pixel is very dark, make transparent
        if r < threshold and g < threshold and b < threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    
    img.putdata(new_data)
    return img


def crop_to_content(img: Image.Image, padding: int = 0) -> Image.Image:
    """Crop transparent image to content bounding box + padding."""
    if img.mode != "RGBA":
        return img
    
    bbox = img.getbbox()
    if bbox is None:
        return img
    
    left, upper, right, lower = bbox
    # Add padding
    left = max(0, left - padding)
    upper = max(0, upper - padding)
    right = min(img.width, right + padding)
    lower = min(img.height, lower + padding)
    
    return img.crop((left, upper, right, lower))


def fit_square(img: Image.Image, size: int, bg_color=(0, 0, 0, 0)) -> Image.Image:
    """Resize image to fit within size x size, preserving aspect ratio."""
    ratio = min(size / img.width, size / img.height)
    new_size = (int(img.width * ratio), int(img.height * ratio))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Create square canvas
    result = Image.new("RGBA", (size, size), bg_color)
    offset = ((size - new_size[0]) // 2, (size - new_size[1]) // 2)
    result.paste(resized, offset, resized if resized.mode == "RGBA" else None)
    return result


def main():
    project_root = Path(__file__).resolve().parent.parent
    public_dir = project_root / "frontend" / "public"
    images_dir = public_dir / "images"
    
    master_path = images_dir / "logo.png"
    if not master_path.exists():
        print(f"ERROR: Master logo not found at {master_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading master logo from {master_path}...")
    master = Image.open(master_path)
    print(f"  Size: {master.size}, Mode: {master.mode}")
    
    # Generate transparent version
    print("Removing black background...")
    transparent = remove_black_bg(master, threshold=35)
    
    # Crop to content for cleaner variants
    cropped = crop_to_content(transparent, padding=20)
    print(f"  Cropped to: {cropped.size}")
    
    # --- Icon variants ---
    print("Generating icon variants...")
    
    # logo-icon.png (512x512, opaque black bg)
    icon_opaque = fit_square(cropped.convert("RGBA"), 512, bg_color=(10, 10, 15, 255))
    icon_opaque = Image.alpha_composite(
        Image.new("RGBA", (512, 512), (10, 10, 15, 255)),
        icon_opaque
    ).convert("RGB")
    icon_opaque.save(images_dir / "logo-icon.png")
    print(f"  ✓ logo-icon.png (512x512)")
    
    # logo-icon-transparent.png (1024x1024, transparent bg)
    icon_trans = fit_square(cropped, 1024)
    icon_trans.save(images_dir / "logo-icon-transparent.png")
    print(f"  ✓ logo-icon-transparent.png (1024x1024)")
    
    # logo-icon-tight.png (512x512, tight crop, transparent bg)
    icon_tight = fit_square(cropped, 512)
    icon_tight.save(images_dir / "logo-icon-tight.png")
    print(f"  ✓ logo-icon-tight.png (512x512)")
    
    # --- Banner variants (wider aspect ratio for header) ---
    print("Generating banner variants...")
    
    # For banner, we use the cropped icon centered in a wide canvas
    banner_w, banner_h = 850, 440
    
    # logo-banner.png (opaque dark bg)
    banner_canvas = Image.new("RGBA", (banner_w, banner_h), (10, 10, 15, 255))
    banner_icon = fit_square(cropped, banner_h - 40)
    offset_x = (banner_w - banner_icon.width) // 2
    banner_canvas.paste(banner_icon, (offset_x, 20), banner_icon)
    banner_canvas.convert("RGB").save(images_dir / "logo-banner.png")
    print(f"  ✓ logo-banner.png ({banner_w}x{banner_h})")
    
    # logo-banner-transparent.png (transparent bg)
    banner_trans = Image.new("RGBA", (banner_w, banner_h), (0, 0, 0, 0))
    banner_trans.paste(banner_icon, (offset_x, 20), banner_icon)
    banner_trans.save(images_dir / "logo-banner-transparent.png")
    print(f"  ✓ logo-banner-transparent.png ({banner_w}x{banner_h})")
    
    # logo-transparent.png (same as banner-transparent for backward compat)
    banner_trans.save(images_dir / "logo-transparent.png")
    print(f"  ✓ logo-transparent.png ({banner_w}x{banner_h})")
    
    # --- Favicon ---
    print("Generating favicon...")
    
    # favicon.png (256x256)
    favicon = fit_square(cropped, 256)
    favicon.save(public_dir / "favicon.png")
    print(f"  ✓ favicon.png (256x256)")
    
    # favicon.ico (multi-size: 16, 32, 48)
    favicon_16 = fit_square(cropped, 16)
    favicon_32 = fit_square(cropped, 32)
    favicon_48 = fit_square(cropped, 48)
    
    favicon_48.save(
        public_dir / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[favicon_16, favicon_32]
    )
    print(f"  ✓ favicon.ico (16/32/48)")
    
    # Also save as jpeg for HTML reference (opaque bg)
    favicon_jpeg = Image.new("RGB", (256, 256), (10, 10, 15))
    favicon_jpeg.paste(favicon, (0, 0), favicon)
    favicon_jpeg.save(public_dir / "favicon.jpeg", quality=90)
    print(f"  ✓ favicon.jpeg (256x256)")
    
    print("\n✅ All logo variants generated successfully!")
    print(f"   Output directory: {images_dir}")


if __name__ == "__main__":
    main()
