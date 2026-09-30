"""Overlay the transparent brand logo onto the top-left corner of an image.

The logo keeps its alpha channel, so the background shows through around it.
Deterministic and free: no API calls.

Usage:
    .venv/bin/python tools/overlay_logo.py --image .tmp/raw.png --out output/linked-in-post/final.png \
        [--logo "brand-assets/G-Force logo  transparency.png"] [--width-pct 13] [--margin-pct 4] [--glow 0.45]

--glow paints a soft teal radial glow behind the logo (0 disables) so the navy parts of the
logo stay legible even when the generated background is plain navy there.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

DEFAULT_LOGO = Path("brand-assets/G-Force logo  transparency.png")
GLOW_RGB = (47, 181, 163)  # brand glow teal #2FB5A3


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--image", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--logo", default=DEFAULT_LOGO, type=Path)
    p.add_argument("--width-pct", default=13.0, type=float, help="Logo width as %% of image width")
    p.add_argument("--margin-pct", default=4.0, type=float, help="Top/left margin as %% of image width")
    p.add_argument("--glow", default=0.45, type=float, help="Opacity (0-1) of the teal glow behind the logo; 0 disables")
    args = p.parse_args()

    base = Image.open(args.image).convert("RGBA")
    logo = Image.open(args.logo).convert("RGBA")

    # Trim the transparent padding so size and margin apply to the visible mark.
    bbox = logo.getchannel("A").getbbox()
    if bbox:
        logo = logo.crop(bbox)

    target_w = round(base.width * args.width_pct / 100)
    target_h = round(logo.height * target_w / logo.width)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)

    margin = round(base.width * args.margin_pct / 100)

    if args.glow > 0:
        # Soft radial glow centered on the logo, fading smoothly into the background (no edges).
        cx, cy = margin + target_w // 2, margin + target_h // 2
        r = round(max(target_w, target_h) * 0.9)
        mask = Image.new("L", base.size, 0)
        ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=round(255 * min(args.glow, 1)))
        mask = mask.filter(ImageFilter.GaussianBlur(r * 0.6))
        glow = Image.new("RGBA", base.size, GLOW_RGB + (0,))
        glow.putalpha(mask)
        base.alpha_composite(glow)

    base.alpha_composite(logo, dest=(margin, margin))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(args.out, "PNG")
    print(f"Saved: {args.out} ({base.width}x{base.height}, logo {target_w}x{target_h} at {margin},{margin})")


if __name__ == "__main__":
    main()
