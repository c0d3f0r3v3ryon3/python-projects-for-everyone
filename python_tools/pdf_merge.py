# pdf_merge.py
from fpdf import FPDF
import os

pdf = FPDF()
for img in os.listdir("downloaded_images"):
    if img.endswith(".jpg"):
        pdf.add_page()
        pdf.image(f"downloaded_images/{img}", 0, 0, 210, 297)
pdf.output("merged.pdf")

print("✅ PDF создан!")
