import os
import struct
from io import BytesIO
from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS_DIR = os.path.join(BASE_DIR, "src-tauri", "icons")

BRAND_PRIMARY = (124, 108, 191)      # #7c6cbf
BRAND_LIGHT = (196, 181, 253)        # #c4b5fd
BRAND_DARK = (90, 76, 150)           # #5a4c96

def create_icon(size):
    """Create a rounded-square placeholder icon with a stylized brush."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background rounded square
    radius = int(size * 0.22)
    margin = int(size * 0.06)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=BRAND_PRIMARY,
    )

    # Simple brush/pen shape (diagonal bar with rounded ends)
    cx, cy = size // 2, size // 2
    length = int(size * 0.55)
    width = int(size * 0.12)
    angle = -45  # degrees

    import math
    rad = math.radians(angle)
    dx = int((length / 2) * math.cos(rad))
    dy = int((length / 2) * math.sin(rad))

    x1, y1 = cx - dx, cy - dy
    x2, y2 = cx + dx, cy + dy

    # Pen body
    draw.line([(x1, y1), (x2, y2)], fill=BRAND_LIGHT, width=width)
    # Rounded caps (approximated with circles)
    cap_r = width // 2
    draw.ellipse([x1 - cap_r, y1 - cap_r, x1 + cap_r, y1 + cap_r], fill=BRAND_LIGHT)
    draw.ellipse([x2 - cap_r, y2 - cap_r, x2 + cap_r, y2 + cap_r], fill=BRAND_LIGHT)

    # Pen tip accent (small darker triangle-ish at lower end)
    tip_x, tip_y = x1, y1
    draw.ellipse(
        [tip_x - cap_r, tip_y - cap_r, tip_x + cap_r, tip_y + cap_r],
        fill=BRAND_DARK,
    )

    # Small highlight dot
    dot_r = int(size * 0.055)
    dot_cx = cx + int(size * 0.18)
    dot_cy = cy - int(size * 0.18)
    draw.ellipse(
        [dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
        fill=BRAND_LIGHT,
    )

    return img


def write_icns(images, path):
    """Write a minimal PNG-based .icns file from a dict of {type_code: PIL Image}."""
    # PNG type codes for modern macOS icons
    chunks = []
    for code, img in images.items():
        buf = BytesIO()
        img.save(buf, format="PNG")
        png_data = buf.getvalue()
        chunk = code.encode("ascii") + struct.pack(">I", len(png_data) + 8) + png_data
        chunks.append(chunk)

    body = b"".join(chunks)
    header = b"icns" + struct.pack(">I", len(body) + 8)
    with open(path, "wb") as f:
        f.write(header + body)


def write_ico(images, path):
    """Write a multi-resolution .ico file embedding PNG data for each size."""
    # images: list of (width, height, PIL Image)
    png_data_list = []
    for _, _, img in images:
        buf = BytesIO()
        img.save(buf, format="PNG")
        png_data_list.append(buf.getvalue())

    count = len(images)
    header = struct.pack("<HHH", 0, 1, count)

    offset = 6 + count * 16
    directory = b""
    data = b""
    for (w, h, _), png in zip(images, png_data_list):
        # Width/height are bytes; 0 means 256
        wb = 0 if w >= 256 else w
        hb = 0 if h >= 256 else h
        size = len(png)
        directory += struct.pack("<BBBBHHII", wb, hb, 0, 0, 1, 32, size, offset)
        data += png
        offset += size

    with open(path, "wb") as f:
        f.write(header + directory + data)


def main():
    os.makedirs(ICONS_DIR, exist_ok=True)

    # Generate master and key sizes
    sizes = {
        "master": 1024,
        32: 32,
        128: 128,
        256: 256,
    }
    images = {k: create_icon(v) for k, v in sizes.items()}

    # Save high-res source for tauri icon command
    source_path = os.path.join(BASE_DIR, "app-icon.png")
    images["master"].save(source_path)

    # Also save explicit PNGs as fallback
    images[32].save(os.path.join(ICONS_DIR, "32x32.png"))
    images[128].save(os.path.join(ICONS_DIR, "128x128.png"))
    images[256].save(os.path.join(ICONS_DIR, "128x128@2x.png"))

    print("Generated icons in", ICONS_DIR)
    for f in sorted(os.listdir(ICONS_DIR)):
        print(" -", f)


if __name__ == "__main__":
    main()
