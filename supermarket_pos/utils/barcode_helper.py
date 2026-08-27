from pathlib import Path
from typing import Optional

import qrcode
from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent.parent
LABELS_DIR = BASE_DIR / "assets" / "labels"
LABELS_DIR.mkdir(parents=True, exist_ok=True)


def generate_qr_image(data: str, filename: Optional[str] = None) -> str:
    if not filename:
        safe_data = data.replace("/", "_").replace(" ", "_")
        filename = f"qr_{safe_data}.png"

    output_path = LABELS_DIR / filename

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)

    return str(output_path)


def generate_product_label(barcode: str, name: str, price: float) -> str:
    qr_path = generate_qr_image(barcode, f"qr_{barcode}.png")
    qr_img = Image.open(qr_path).resize((180, 180))

    label = Image.new("RGB", (420, 220), "white")
    draw = ImageDraw.Draw(label)
    label.paste(qr_img, (10, 20))

    try:
        font_title = ImageFont.truetype("DejaVuSans.ttf", 20)
        font_text = ImageFont.truetype("DejaVuSans.ttf", 16)
    except Exception:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    draw.text((210, 30), name, fill="black", font=font_title)
    draw.text((210, 80), f"Barcode: {barcode}", fill="black", font=font_text)
    draw.text((210, 120), f"Price: {price:.2f}", fill="black", font=font_text)

    output_path = LABELS_DIR / f"label_{barcode}.png"
    label.save(output_path)
    return str(output_path)
