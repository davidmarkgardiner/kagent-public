#!/usr/bin/env python3
"""Embed Virgil + Cascadia woff2 fonts inline as base64 data URIs in each SVG.

The Excalidraw export uses @font-face with `src: url("https://excalidraw.com/Virgil.woff2")`
which fails to fetch when the SVG is rendered offline (e.g. in Marp's headless
Chromium during PDF generation). Replacing the URL with a base64 data URI
guarantees the playful Virgil hand-drawn font renders everywhere.
"""

from __future__ import annotations
import base64
import glob
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(DIR, ".fonts")


def load_font(name: str) -> str:
    path = os.path.join(FONT_DIR, f"{name}.woff2")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main():
    virgil_b64 = load_font("Virgil")
    cascadia_b64 = load_font("Cascadia")

    for svg in glob.glob(os.path.join(DIR, "*.svg")):
        with open(svg, "r") as f:
            content = f.read()

        # Replace the two stock @font-face src URLs with inline data URIs.
        new_content = re.sub(
            r'src:\s*url\("https://excalidraw\.com/Virgil\.woff2"\)',
            f'src: url(data:font/woff2;base64,{virgil_b64}) format("woff2")',
            content,
        )
        new_content = re.sub(
            r'src:\s*url\("https://excalidraw\.com/Cascadia\.woff2"\)',
            f'src: url(data:font/woff2;base64,{cascadia_b64}) format("woff2")',
            new_content,
        )

        if new_content == content:
            print(f"  - {os.path.basename(svg)}: no @font-face url to replace")
            continue

        with open(svg, "w") as f:
            f.write(new_content)
        print(f"  ✓ {os.path.basename(svg)}: embedded fonts ({len(new_content)} bytes)")


if __name__ == "__main__":
    main()
