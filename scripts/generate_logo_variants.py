#!/usr/bin/env python3
"""Generate logo variants and favicon from the new master logo.

Input:  frontend/public/images/logo.png (1254x1254, RGB, dark bg)
Output: all variants in frontend/public/images/ and frontend/public/favicon.*
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
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


def make_full_favicon(img: Image.Image, size: int, add_rim: bool = True) -> Image.Image:
    """Generate high-impact rounded favicon using the naturally rounded camera icon.
    
    Fills the frame edge-to-edge with minimal margin so it appears large, bold,
    and prominent in browser tabs without nested box-in-box margins.
    """
    scale = 4
    canvas_size = size * scale
    pad = int(canvas_size * 0.02)  # minimal 2% margin to avoid anti-aliasing edge clipping
    inner = canvas_size - 2 * pad
    
    ratio = min(inner / img.width, inner / img.height)
    new_w = max(1, int(img.width * ratio))
    new_h = max(1, int(img.height * ratio))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    pos_x = (canvas_size - new_w) // 2
    pos_y = (canvas_size - new_h) // 2
    canvas.paste(resized, (pos_x, pos_y), resized)
    
    if add_rim:
        # Subtle rim highlight around the silhouette for definition on dark tabs
        alpha = canvas.split()[3]
        rim_mask = alpha.filter(ImageFilter.MaxFilter(scale * 2 + 1))
        
        rim_layer = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
        rim_data = []
        for a_rim, a_orig in zip(rim_mask.getdata(), alpha.getdata()):
            if a_rim > 0 and a_orig == 0:
                rim_data.append((255, 255, 255, min(42, int(a_rim * 0.22))))
            else:
                rim_data.append((0, 0, 0, 0))
        rim_layer.putdata(rim_data)
        canvas = Image.alpha_composite(rim_layer, canvas)
        
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


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
    
    # Tight crop for favicon (exact camera icon boundary, full bleed)
    cropped_tight = transparent.crop(transparent.getbbox())
    # Crop with padding for banner/icon variants
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
    
    # --- Favicon (Large, Bold, Naturally Rounded) ---
    print("Generating favicon...")
    
    # favicon.png (256x256, large rounded camera icon)
    favicon_256 = make_full_favicon(cropped_tight, 256)
    favicon_256.save(public_dir / "favicon.png")
    print(f"  ✓ favicon.png (256x256, large rounded)")
    
    # Standard multi-resolution sizes for web browsers & bookmarks
    favicon_48 = make_full_favicon(cropped_tight, 48)
    favicon_32 = make_full_favicon(cropped_tight, 32)
    favicon_32.save(public_dir / "favicon-32x32.png")
    print(f"  ✓ favicon-32x32.png (32x32)")
    
    favicon_16 = make_full_favicon(cropped_tight, 16)
    favicon_16.save(public_dir / "favicon-16x16.png")
    print(f"  ✓ favicon-16x16.png (16x16)")

    # apple-touch-icon.png (180x180)
    apple_touch = make_full_favicon(cropped_tight, 180)
    apple_touch.save(public_dir / "apple-touch-icon.png")
    print(f"  ✓ apple-touch-icon.png (180x180)")
    
    # favicon.ico (multi-size: 16, 32, 48)
    favicon_48.save(
        public_dir / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=[favicon_16, favicon_32],
    )
    print(f"  ✓ favicon.ico (16/32/48, large rounded)")
    
    # Also save favicon.jpeg with rounded badge on dark background for backward compat
    favicon_jpeg_canvas = Image.new("RGB", (256, 256), (10, 10, 15))
    favicon_jpeg_canvas.paste(favicon_256, (0, 0), favicon_256)
    favicon_jpeg_canvas.save(public_dir / "favicon.jpeg", quality=95)
    print(f"  ✓ favicon.jpeg (256x256, fallback)")
    
    print("\n✅ All logo variants generated successfully!")
    print(f"   Output directory: {images_dir}")


if __name__ == "__main__":
    main()
