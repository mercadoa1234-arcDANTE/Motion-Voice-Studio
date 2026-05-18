# Source-Doc Flow — v3

How a source paper (PDF, Substack post, website) becomes visual content in the video.

## The principle

An educational video that adapts a source paper should SHOW the paper. Viewers want to know:

- What document are we drawing from?
- Who wrote it?
- Which figure is being discussed?
- Where can they find it themselves?

v3 ingests the source ONCE upfront, extracts its pages and figures and metadata, and the storyboard references those assets like any other image. The final video weaves the paper screenshots in at appropriate beats:

- **Chapter intro:** page 1 of the paper (title page or hero figure) for ~3-5s while the narrator says "From Canosa 2024…"
- **Body shots:** the specific figure being analyzed appears as a 4-6s image-shot before the explainer animation.
- **Credits:** the acknowledgements section + reference list as final cards.

## The pipeline

### 1. Ingest

```bash
python scripts/source_doc_pass.py /mnt/user-data/uploads/canosa_paper.pdf \
    --out /home/claude/production/<project>/assets/source_docs/canosa_137/
```

Produces:
```
assets/source_docs/canosa_137/
├── page_001.png    page_002.png    ... page_NNN.png
├── figures/
│   ├── fig-001.png
│   ├── fig-002.png
│   └── ...
├── metadata.json
└── SOURCE_DOC_README.md
```

Where `metadata.json` has structured fields:
```json
{
  "source_path": "...",
  "title": "37, 137, and the Origin of the Solfeggios",
  "authors": "Anthony Canosa",
  "page_count": 14,
  "figures": [...],
  "acknowledgements": "Thanks to ...",
  "references_excerpt": "..."
}
```

### 2. Reference in the storyboard

Any shot can use `engine: "image"` with the source-doc path:

```json
{
  "id": "intro_paper",
  "render": {
    "engine": "image",
    "src": "assets/source_docs/canosa_137/page_001.png",
    "caption": "Canosa 2024 · the source",
    "attribution": "Substack · 101E8E8",
    "ken_burns": {"zoom": 1.08, "pan": [0.0, -0.05]},
    "fade_in_s": 0.4,
    "fade_out_s": 0.4
  },
  "narration": "This series adapts Anthony Canosa's 2024 paper, Thirty-Seven, One-Thirty-Seven, and the Hidden Architecture of Number."
}
```

### 3. Render flow

The orchestrator's `image` engine handles letterboxing, Ken Burns zoom/pan, and fade in/out. The viewer sees the actual page, fully readable at 1280×720, with a gold caption above and gray attribution below.

## Typical placement in a 4-chapter series

| Chapter | Placement | Why |
|---|---|---|
| 1 intro | Page 1 of source paper, 4s with Ken Burns slow zoom | Establishes authority |
| 1.5 body | Figure 1 of source (the prime-cross diagram), 4s static | Anchors the claim being explained |
| 4 closing | Acknowledgements page, 5s static | Honors the author |
| 4 credits | Reference list, 5s | Names the prior work |

Don't overdo it. A 20-minute series should use 4-6 image-shots total. The image-shot engine is a citation tool, not a screen-saver.

## Author / hero figure handling

`metadata.json` carries the title + authors. The chapter intro should ALWAYS verbally cite the author by name:

```
"This chapter adapts the work of Anthony Canosa, published in 2024 on Substack."
```

The image-shot beneath shows the actual page header. The viewer hears + sees the attribution simultaneously. That's how citations work in a video.

## Acknowledgements and references

`source_doc_pass.py` extracts both the "Acknowledgements" section and the "References" section from the PDF text. These go into `metadata.json`.

The storyboard's final scenes should be:

```json
{
  "id": "ack_card",
  "render": {
    "engine": "image",
    "src": "assets/source_docs/canosa_137/page_013.png",
    "caption": "Acknowledgements",
    "fade_in_s": 0.5, "fade_out_s": 0.5
  },
  "narration": "The author thanks the readers of his Substack who pushed the construction further."
},
{
  "id": "refs_card",
  "render": {
    "engine": "image",
    "src": "assets/source_docs/canosa_137/page_014.png",
    "caption": "References & further reading"
  },
  "duration": 5.0
}
```

## Handling URLs (Substack posts, blog posts)

For URLs:

```bash
python scripts/source_doc_pass.py https://101e8e8.substack.com/p/the-architecture \
    --out /home/claude/production/<project>/assets/source_docs/canosa_substack/
```

Uses headless chromium (if installed) to capture a full-page screenshot. If no headless browser is available, falls back to saving the raw HTML.

For Substack specifically: the post often spans 4-5 vertical screens. The headless capture uses `--window-size=1280,3000` to grab the full vertical extent — then `image_shot` can pan down the page with Ken Burns to reveal the content while the narrator reads.

## What NOT to do

- **Don't insert image-shots without verbal citation.** Just showing the page without saying whose work it is = bad citation practice.
- **Don't blow up tiny figures** to fill the screen. Letterbox and let the original aspect ratio breathe. The image-shot engine does this by default.
- **Don't crop the page header off.** The title is part of the citation.
- **Don't insert every page.** Curate. 4-6 page references in a 20-minute series is plenty.
- **Don't forget to verify** that the figures you cite are actually present. `pdfimages` extracts ALL embedded raster images — including page-header logos, watermarks, and decorative borders. Hand-curate which are real figures before storyboarding them.
