#!/usr/bin/env python3
"""Rebuild the visual-only PDF from the nine included slide images."""
import json
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

root = Path(__file__).resolve().parent
slides = json.loads((root / 'manifest.json').read_text())
output = root / 'visual-slides.pdf'
pdf = canvas.Canvas(str(output), pagesize=(960, 540), pageCompression=1)
pdf.setTitle('DICE agent journey - visual slides')
pdf.setAuthor('DICE')
pdf.setSubject('Visual companion to the ordered YAML walkthrough; code slides omitted')
for slide in slides:
    pdf.bookmarkPage(slide['id'])
    pdf.addOutlineEntry(slide['title'], slide['id'], level=0)
    pdf.drawImage(ImageReader(str(root / slide['file'])), 0, 0, width=960, height=540)
    pdf.showPage()
pdf.save()
print(f'{len(slides)} visual pages written to {output.name}')
