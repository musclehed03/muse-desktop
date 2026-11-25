#!/usr/bin/env python3
"""Generate the Baxter - Our Deviant Muse icon set.

Design (Posh Luxe Variant A, metal SOPs):
- Near-black rounded-square badge (#101117 family).
- Frame: PLAIN metallic brushed SILVER pinstripe ring (utility).
- Hairline: neon pink #FF1E89 ring just inside the silver frame (brand).
- Mark: GLOSSY metallic GOLD "B" (refinement) with the gleam on the
  upper-right (EAST light, 45 deg) and the shadow to the lower-left.
- Ornament: ONE small GLOSSY PLATINUM diamond, upper-right.
- No flat gray/gold fills anywhere metal belongs: every metal surface is a
  gradient with a specular band; brushed silver carries fine brushing noise.
- Pinstripe glow: crisp hard steps, blur radius 0 on the glow lines.

Outputs: build/icon.png (1024), build/icons/{16,24,32,48,64,96,128,256,512,1024}.png,
build/icon.svg (same composition as vector), build/icon.icns (via Pillow).
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(REPO, "build")
ICONS_DIR = os.path.join(BUILD, "icons")
S = 1024
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# --- ramps: (t, (r, g, b)) along the NE axis, t=0 bottom-left, t=1 top-right ---
GOLD_GLOSSY = [
    (0.00, (0x4A, 0x2F, 0x08)),
    (0.25, (0x8A, 0x64, 0x14)),
    (0.45, (0xC1, 0x93, 0x1F)),
    (0.60, (0xE3, 0xB6, 0x2E)),
    (0.72, (0xF7, 0xDD, 0x6E)),
    (0.82, (0xFF, 0xF0, 0xA0)),
    (0.88, (0xFF, 0xFB, 0xE0)),  # specular peak
    (0.94, (0xF2, 0xCD, 0x54)),
    (1.00, (0xB9, 0x8D, 0x1C)),
]
SILVER_BRUSHED = [
    (0.00, (0x76, 0x7B, 0x85)),
    (0.30, (0x9A, 0xA0, 0xAA)),
    (0.55, (0xC6, 0xCA, 0xD2)),
    (0.75, (0xE2, 0xE5, 0xEA)),
    (1.00, (0xB4, 0xB9, 0xC1)),
]
PLATINUM_GLOSSY = [
    (0.00, (0x5D, 0x61, 0x67)),
    (0.30, (0x87, 0x8C, 0x94)),
    (0.55, (0xC3, 0xC8, 0xD0)),
    (0.75, (0xEE, 0xF0, 0xF3)),
    (0.85, (0xFF, 0xFF, 0xFF)),  # specular peak
    (1.00, (0xA9, 0xAE, 0xB6)),
]
PINK = (0xFF, 0x1E, 0x89)
PINK_LIGHT = (0xFF, 0x8A, 0xC2)


def ramp(stops, t):
    """Interpolate a color ramp. t is a float array in [0, 1]."""
    ts = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=np.float64)
    out = np.zeros(t.shape + (3,), dtype=np.float64)
    for c in range(3):
        out[..., c] = np.interp(t, ts, cols[:, c])
    return out


def ne_axis(shape):
    """t in [0,1] increasing toward the upper-right (EAST light, 45 deg)."""
    h, w = shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    return np.clip(0.5 + (x - (h - 1 - y)) / (2.0 * max(h, w)), 0.0, 1.0)


def brushed_noise(shape, seed=7, amp=7.0):
    """Fine horizontal brushing: per-row brightness jitter."""
    rng = np.random.default_rng(seed)
    h, w = shape
    row = rng.normal(0.0, amp, size=(h, 1))
    col = rng.normal(0.0, amp * 0.35, size=(1, w))
    return row + col


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    t = ne_axis((S, S))

    # --- badge background: near-black radial falloff ---
    y, x = np.mgrid[0:S, 0:S].astype(np.float64)
    cx = cy = S / 2
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (S / 2)
    bg = np.zeros((S, S, 3), dtype=np.float64)
    bg[..., 0] = np.interp(r, [0, 1], [0x19, 0x0A])
    bg[..., 1] = np.interp(r, [0, 1], [0x1A, 0x0A])
    bg[..., 2] = np.interp(r, [0, 1], [0x20, 0x0F])
    bg_img = Image.fromarray(np.dstack([bg, np.full((S, S), 255)]).astype(np.uint8), "RGBA")
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, S - 1, S - 1], radius=190, fill=255)
    img.paste(bg_img, (0, 0), mask)

    draw = ImageDraw.Draw(img)

    # --- silver pinstripe frame: plain metallic, brushed (utility) ---
    silver = ramp(SILVER_BRUSHED, t) + brushed_noise((S, S))[..., None]
    silver_img = Image.fromarray(
        np.dstack([np.clip(silver, 0, 255), np.full((S, S), 255)]).astype(np.uint8), "RGBA"
    )
    ring = Image.new("L", (S, S), 0)
    rd = ImageDraw.Draw(ring)
    rd.rounded_rectangle([30, 30, S - 31, S - 31], radius=165, outline=255, width=10)
    img.paste(silver_img, (0, 0), ring)

    # --- pink hairline just inside the silver frame (brand) ---
    draw.rounded_rectangle([48, 48, S - 49, S - 49], radius=150, outline=PINK + (255,), width=3)

    # --- glossy gold "B" (refinement), gleam upper-right, shadow lower-left ---
    font = ImageFont.truetype(FONT_PATH, 640)
    glyph = Image.new("L", (S, S), 0)
    gd = ImageDraw.Draw(glyph)
    bbox = gd.textbbox((0, 0), "B", font=font)
    gw, gh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    gx, gy = (S - gw) // 2 - bbox[0], (S - gh) // 2 - bbox[1] + 18
    gd.text((gx, gy), "B", font=font, fill=255)
    # shadow to the lower-left (180 deg opposite the east light)
    sh = Image.new("L", (S, S), 0)
    sh.paste(glyph, (-12, 14))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    shadow = Image.new("RGBA", (S, S), (0x1A, 0x10, 0x02, 0))
    shadow.putalpha(sh.point(lambda v: int(v * 0.55)))
    img.alpha_composite(shadow)
    gold = ramp(GOLD_GLOSSY, t)
    gold_img = Image.fromarray(
        np.dstack([np.clip(gold, 0, 255), np.full((S, S), 255)]).astype(np.uint8), "RGBA"
    )
    img.paste(gold_img, (0, 0), glyph)
    # GLOSSY specular band: hard-edged diagonal stripe across the B's
    # upper-right (east light), clipped to the glyph. No blur — hard steps.
    bar = Image.new("L", (S, S), 0)
    bar_d = ImageDraw.Draw(bar)
    bar_d.rectangle([630 - 60, 400 - 320, 630 + 60, 400 + 320], fill=190)
    bar = bar.rotate(45, resample=Image.BICUBIC, center=(630, 400))
    spec = Image.new("RGBA", (S, S), (0xFF, 0xFB, 0xE0, 0))
    spec.putalpha(bar)
    spec_mask = Image.composite(spec, Image.new("RGBA", (S, S), (0, 0, 0, 0)), glyph)
    img.alpha_composite(spec_mask)

    # --- one small glossy platinum diamond ornament, upper-right ---
    # Faceted: upper-right facet near-white, lower-left facet mid-gray.
    cxo, cyo, d = 788, 232, 46
    facet_hi = Image.new("L", (S, S), 0)
    fh = ImageDraw.Draw(facet_hi)
    fh.polygon([(cxo, cyo - d), (cxo + d, cyo), (cxo, cyo + d)], fill=255)
    facet_lo = Image.new("L", (S, S), 0)
    fl = ImageDraw.Draw(facet_lo)
    fl.polygon([(cxo, cyo - d), (cxo, cyo + d), (cxo - d, cyo)], fill=255)
    plat_hi = Image.new("RGBA", (S, S), (0xF4, 0xF6, 0xF9, 255))
    plat_lo = Image.new("RGBA", (S, S), (0x9A, 0xA0, 0xA8, 255))
    img.paste(plat_hi, (0, 0), facet_hi)
    img.paste(plat_lo, (0, 0), facet_lo)
    # crisp platinum edge, 2px, no blur (pinstripe glow: hard steps)
    draw.polygon(
        [(cxo, cyo - d), (cxo + d, cyo), (cxo, cyo + d), (cxo - d, cyo)],
        outline=(0xFF, 0xFF, 0xFF, 255),
        width=2,
    )

    # --- outputs ---
    os.makedirs(ICONS_DIR, exist_ok=True)
    img.save(os.path.join(BUILD, "icon.png"))
    for size in (16, 24, 32, 48, 64, 96, 128, 256, 512, 1024):
        small = img.resize((size, size), Image.LANCZOS)
        small.save(os.path.join(ICONS_DIR, f"{size}x{size}.png"))
    try:
        img.save(os.path.join(BUILD, "icon.icns"))
        print("icns: ok")
    except Exception as exc:  # noqa: BLE001 - Pillow ICNS is best-effort
        print(f"icns: skipped ({exc})")
    print(f"icon set written: {BUILD}/icon.png + {ICONS_DIR}/{{16..1024}}x{{16..1024}}.png")


def write_svg():
    """Vector twin of the PNG icon: same composition, B as a glyph path."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.ttLib import TTFont

    f = TTFont(FONT_PATH)
    glyphset = f.getGlyphSet()
    pen = SVGPathPen(glyphset)
    glyphset["B"].draw(pen)
    b_path = pen.getCommands()
    glyf = f["glyf"]["B"]
    upem = f["head"].unitsPerEm
    scale = 640 / upem
    gw = (glyf.xMax - glyf.xMin) * scale
    gh = (glyf.yMax - glyf.yMin) * scale
    # same centering as the PNG version (font Y is up; flip in transform)
    tx = (S - gw) / 2 - glyf.xMin * scale
    ty = (S + gh) / 2 + 18 + glyf.yMin * scale
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="72%">
      <stop offset="0%" stop-color="#191a20"/>
      <stop offset="100%" stop-color="#0a0a0f"/>
    </radialGradient>
    <linearGradient id="silver" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#767b85"/>
      <stop offset="30%" stop-color="#9aa0aa"/>
      <stop offset="55%" stop-color="#c6cad2"/>
      <stop offset="75%" stop-color="#e2e5ea"/>
      <stop offset="100%" stop-color="#b4b9c1"/>
    </linearGradient>
    <linearGradient id="gold" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#4a2f08"/>
      <stop offset="25%" stop-color="#8a6414"/>
      <stop offset="45%" stop-color="#c1931f"/>
      <stop offset="60%" stop-color="#e3b62e"/>
      <stop offset="72%" stop-color="#f7dd6e"/>
      <stop offset="82%" stop-color="#fff0a0"/>
      <stop offset="88%" stop-color="#fffbe0"/>
      <stop offset="94%" stop-color="#f2cd54"/>
      <stop offset="100%" stop-color="#b98d1c"/>
    </linearGradient>
    <clipPath id="bclip"><path d="{b_path}" transform="translate({tx:.1f} {ty:.1f}) scale({scale} {-scale})"/></clipPath>
  </defs>
  <rect x="0" y="0" width="1024" height="1024" rx="190" fill="url(#bg)"/>
  <rect x="30" y="30" width="964" height="964" rx="165" fill="none" stroke="url(#silver)" stroke-width="10"/>
  <rect x="48" y="48" width="928" height="928" rx="150" fill="none" stroke="#ff1e89" stroke-width="3"/>
  <path d="{b_path}" transform="translate({tx:.1f} {ty:.1f}) scale({scale} {-scale})" fill="url(#gold)"/>
  <g clip-path="url(#bclip)">
    <rect x="570" y="80" width="120" height="640" fill="#fffbe0" opacity="0.75" transform="rotate(45 630 400)"/>
  </g>
  <polygon points="788,186 834,232 788,278" fill="#f4f6f9"/>
  <polygon points="788,186 788,278 742,232" fill="#9aa0a8"/>
  <polygon points="788,186 834,232 788,278 742,232" fill="none" stroke="#ffffff" stroke-width="2"/>
</svg>
"""
    with open(os.path.join(BUILD, "icon.svg"), "w") as fh:
        fh.write(svg)
    print("svg: ok")


if __name__ == "__main__":
    main()
    write_svg()
