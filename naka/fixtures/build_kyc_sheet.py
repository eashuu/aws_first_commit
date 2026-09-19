"""Builds the two demo document fixtures (doc 10 §5): a synthetic, watermarked
internal KYC verification sheet — deliberately NOT a replica of a real
Aadhaar card, which would be an avoidable trademark/impersonation problem.

  kyc-sheet-tkt-4471.pdf  single page, A4, Latin only  (ticket tkt_4471)
  kyc-sheet-tkt-4472.png  same page + one Devanagari line (ticket tkt_4472)

Run once during setup: `python fixtures/build_kyc_sheet.py`. Requires
reportlab and Pillow (dev-time only — neither ships in the Lambda zip; the
Lambda reads the generated files as static bytes).
"""

from __future__ import annotations

import os

FOOTER = (
    "Generated for Naka demo. No real person's data appears on this sheet. "
    "The Aadhaar number above begins with 1 - a range UIDAI never issues, "
    "and satisfies the Verhoeff check digit."
)

HERE = os.path.dirname(__file__)


def build_pdf(path: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    c.saveState()
    c.setFillGray(0.88)
    c.setFont("Helvetica-Bold", 40)
    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.drawCentredString(0, 0, "SPECIMEN - SYNTHETIC DATA")
    c.restoreState()

    c.setFillGray(0)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height * 0.94, "CUSTOMER ONBOARDING - KYC VERIFICATION SHEET")

    c.setFont("Helvetica", 9)
    c.setFillGray(0.4)
    c.drawCentredString(width / 2, height * 0.90, "Internal use only . Form KV-2 . Rev 3")

    c.setFillGray(0)
    fields = [
        ("Helvetica", 12, "Applicant Name:  Meera Nair"),
        ("Helvetica", 12, "Date of Birth:  02/11/1992"),
        ("Helvetica", 12, "Residential Address:  27/3 Kadavanthra Lane,"),
        ("Helvetica", 12, "                          Panampilly Nagar, Kochi, Kerala 682036"),
        ("Courier-Bold", 13, "Aadhaar Number:  1639 4058 2713"),
        ("Helvetica", 12, "Verification Status:  Pending officer review"),
    ]
    y = height * 0.76
    for font, size, text in fields:
        c.setFont(font, size)
        c.drawString(width * 0.10, y, text)
        y -= height * 0.06

    c.setFont("Helvetica", 8)
    c.setFillGray(0.3)
    c.drawString(width * 0.10, height * 0.07, FOOTER[:100])
    c.drawString(width * 0.10, height * 0.055, FOOTER[100:])

    c.showPage()
    c.save()


def build_png(path: str) -> None:
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1240, 1754  # A4 @ 150 dpi

    def font(name: str, size: int):
        return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)

    img = Image.new("RGB", (W, H), "white")

    watermark = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    wdraw = ImageDraw.Draw(watermark)
    wdraw.text((W * 0.12, H * 0.46), "SPECIMEN - SYNTHETIC DATA", font=font("arialbd.ttf", 54), fill=(0, 0, 0, 30))
    watermark = watermark.rotate(45, resample=Image.BICUBIC, center=(W // 2, H // 2))
    img.paste(watermark, (0, 0), watermark)

    draw = ImageDraw.Draw(img)
    draw.text((W * 0.5, H * 0.06), "CUSTOMER ONBOARDING - KYC VERIFICATION SHEET", font=font("arialbd.ttf", 26), fill="black", anchor="mm")
    draw.text((W * 0.5, H * 0.10), "Internal use only . Form KV-2 . Rev 3", font=font("arial.ttf", 17), fill=(100, 100, 100), anchor="mm")

    draw.text((W * 0.10, H * 0.24), "Applicant Name:  Meera Nair", font=font("arial.ttf", 22), fill="black")
    draw.text((W * 0.10, H * 0.27), "\u0928\u093e\u092e: \u092e\u0940\u0930\u093e \u0928\u093e\u092f\u0930", font=font("mangal.ttf", 22), fill="black")
    draw.text((W * 0.10, H * 0.30), "Date of Birth:  02/11/1992", font=font("arial.ttf", 22), fill="black")
    draw.text((W * 0.10, H * 0.36), "Residential Address:  27/3 Kadavanthra Lane,", font=font("arial.ttf", 22), fill="black")
    draw.text((W * 0.24, H * 0.40), "Panampilly Nagar, Kochi, Kerala 682036", font=font("arial.ttf", 22), fill="black")
    draw.text((W * 0.10, H * 0.50), "Aadhaar Number:  1639 4058 2713", font=font("cour.ttf", 24), fill="black")
    draw.text((W * 0.10, H * 0.56), "Verification Status:  Pending officer review", font=font("arial.ttf", 22), fill="black")
    draw.text((W * 0.10, H * 0.92), FOOTER, font=font("arial.ttf", 15), fill=(80, 80, 80))

    img.save(path)


if __name__ == "__main__":
    pdf_path = os.path.join(HERE, "kyc-sheet-tkt-4471.pdf")
    png_path = os.path.join(HERE, "kyc-sheet-tkt-4472.png")
    build_pdf(pdf_path)
    build_png(png_path)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")
