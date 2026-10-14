# Visual slides without code

Open the PNGs to the right of the YAML using VS Code's **Open to the Side**. These are the same nine pages as [visual-slides.pdf](visual-slides.pdf), with every YAML/code slide omitted. No extension is needed for PNG preview.

1. [Our journey](01-journey.png)
2. [Gateway isolation](02-isolation.png)
3. [Entra blueprint and child identity](03-entra-blueprint.png)
4. [Triage to reviewed change and verification](04-triage.png)
5. [Connected operational systems](05-connected-systems.png)
6. [SRE orchestration chatbot](06-sre-chatbot.png)
7. [SDLC integration](07-sdlc.png)
8. [Runtime and durability](08-runtime.png)
9. [Journeys and closing](09-journeys.png)

The original HyperFrames deck and optional recorded chapters remain in their existing location. The PDF/PNGs are static visuals; they do not play those chapters or run a demo.

To rebuild the PDF from the included PNGs, run `uv run --with reportlab --with pillow python slides/build-pdf.py` from the walkthrough folder. No browser, cluster or model is needed for that rebuild.
