"""
source_doc_pass.py — v3 source-document ingestion.

When a video adapts a source document (paper, Substack post, PDF, website),
the audience expects to see WHERE the claims come from. This pass extracts:

  1. Page screenshots (rasterized PDF pages or full-page screenshots of a URL)
  2. Document header (title, authors, date) — used in chapter intro card
  3. Acknowledgements / sources / references section — used in end credits
  4. Embedded figures + their captions — used in body shots when the
     storyboard cites them by figure number

Output: /assets/source_docs/<doc_id>/
    page_001.png ... page_NNN.png       (full-page rasters)
    figures/fig_01.png ... fig_NN.png   (cropped figures with caption metadata)
    metadata.json                        (title, authors, ack text, figures index)
    SOURCE_DOC_README.md                  (where this came from + how to cite)

Usage:
    from source_doc_pass import ingest_pdf, ingest_url
    meta = ingest_pdf('paper.pdf', out_dir='assets/source_docs/canosa_137/')
    meta = ingest_url('https://...substack.com/...', out_dir='...')

The storyboard then references these screenshots as image-shot inputs:
    {"engine": "image", "src": "assets/source_docs/.../page_002.png",
     "caption": "Canosa 2024 · §3 · the φ-spiral derivation", ...}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional


# ── PDF ingestion (no extra deps — uses bundled tools) ────────────────────

def ingest_pdf(
    pdf_path: str,
    out_dir: str,
    dpi: int = 150,
    extract_figures: bool = True,
) -> dict:
    """Rasterize PDF pages and extract figures.

    Page rasterization uses pdftoppm (poppler-utils). Figure extraction uses
    pdfimages. Both are standard on most Linux distros and Anthropic sandbox.

    Falls back to PyMuPDF (fitz) if available for richer metadata.
    """
    pdf_path = str(pdf_path)
    out_dir = str(out_dir)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    figs_dir = Path(out_dir) / 'figures'
    figs_dir.mkdir(exist_ok=True)

    # 1. Rasterize pages
    page_prefix = str(Path(out_dir) / 'page')
    subprocess.run([
        'pdftoppm', '-png', '-r', str(dpi),
        pdf_path, page_prefix,
    ], check=True)

    pages = sorted(Path(out_dir).glob('page-*.png')) + sorted(Path(out_dir).glob('page-*.PNG'))
    # pdftoppm uses 1-based page numbering; ensure consistent zero-padded names.
    renamed_pages = []
    for p in pages:
        match = re.search(r'page-(\d+)\.png$', str(p), re.IGNORECASE)
        if not match:
            continue
        n = int(match.group(1))
        new_name = Path(out_dir) / f'page_{n:03d}.png'
        if str(p) != str(new_name):
            os.rename(p, new_name)
        renamed_pages.append(str(new_name))

    # 2. Extract embedded figures
    figure_records = []
    if extract_figures:
        figs_prefix = str(figs_dir / 'fig')
        try:
            subprocess.run([
                'pdfimages', '-png', pdf_path, figs_prefix,
            ], check=True)
            for f in sorted(figs_dir.glob('fig-*.png')):
                figure_records.append({
                    'path': str(f.relative_to(out_dir)),
                    'name': f.stem,
                })
        except (subprocess.CalledProcessError, FileNotFoundError):
            # pdfimages may not be installed; skip silently
            pass

    # 3. Metadata via pdfinfo
    meta = {}
    try:
        out = subprocess.run(['pdfinfo', pdf_path],
                             capture_output=True, text=True, check=True)
        for line in out.stdout.splitlines():
            if ':' in line:
                key, val = line.split(':', 1)
                meta[key.strip()] = val.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 4. Extract text and search for acknowledgements / authors
    title = meta.get('Title', '')
    authors = meta.get('Author', '')
    ack_text = _extract_acknowledgements(pdf_path)
    refs_text = _extract_references(pdf_path)

    metadata = {
        'source_path': pdf_path,
        'kind': 'pdf',
        'title': title,
        'authors': authors,
        'pdfinfo': meta,
        'pages': [str(Path(p).name) for p in renamed_pages],
        'page_count': len(renamed_pages),
        'figures': figure_records,
        'acknowledgements': ack_text,
        'references_excerpt': refs_text,
    }
    (Path(out_dir) / 'metadata.json').write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False)
    )
    _write_readme(out_dir, metadata)
    return metadata


def _extract_text(pdf_path: str) -> str:
    """Try pdftotext; return empty string if not installed."""
    try:
        out = subprocess.run(
            ['pdftotext', '-layout', pdf_path, '-'],
            capture_output=True, text=True, check=True,
        )
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ''


def _extract_acknowledgements(pdf_path: str) -> str:
    text = _extract_text(pdf_path)
    if not text:
        return ''
    # Find a section header that looks like Acknowledgements / Thanks / Credits
    m = re.search(
        r'(?im)^\s*(acknowledg(?:e?ment)?s?|thanks|credits)\s*$',
        text,
    )
    if not m:
        return ''
    start = m.end()
    # End at next section header (e.g., References, Bibliography) or after 1500 chars
    after = text[start:start + 3000]
    end_m = re.search(
        r'(?im)^\s*(references|bibliography|works\s+cited|appendix|notes)\s*$',
        after,
    )
    if end_m:
        return after[:end_m.start()].strip()
    return after.strip()[:1500]


def _extract_references(pdf_path: str) -> str:
    text = _extract_text(pdf_path)
    if not text:
        return ''
    m = re.search(r'(?im)^\s*(references|bibliography|works\s+cited)\s*$', text)
    if not m:
        return ''
    return text[m.start():m.start() + 4000]


# ── URL ingestion (Substack, blog posts, etc.) ────────────────────────────

def ingest_url(
    url: str,
    out_dir: str,
    full_page: bool = True,
) -> dict:
    """Screenshot a webpage. Tries chromium-headless / google-chrome /
    playwright in turn. Returns metadata."""
    out_dir = str(out_dir)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    figs_dir = Path(out_dir) / 'figures'
    figs_dir.mkdir(exist_ok=True)

    page_path = Path(out_dir) / 'page_001.png'

    # Try chromium-based headless first.
    chrome_bin = _find_chrome()
    if chrome_bin:
        cmd = [
            chrome_bin, '--headless', '--disable-gpu', '--no-sandbox',
            '--hide-scrollbars',
            f'--screenshot={page_path}',
            '--window-size=1280,3000',
        ]
        if full_page:
            cmd.append('--virtual-time-budget=5000')
        cmd.append(url)
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f'  [source_doc] chrome screenshot failed: {e}')
            page_path = None
    else:
        page_path = None

    if not page_path or not Path(page_path).exists():
        # Fallback: try curl-based static fetch then complain — full
        # screenshot would need playwright/puppeteer installed by user.
        try:
            html_path = Path(out_dir) / 'page.html'
            subprocess.run(
                ['curl', '-sL', '-o', str(html_path), url],
                check=True, timeout=30,
            )
            print(f'  [source_doc] no headless browser; saved HTML only.')
            page_path = None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    metadata = {
        'source_path': url,
        'kind': 'url',
        'title': '',
        'authors': '',
        'pages': [page_path.name] if page_path and page_path.exists() else [],
        'page_count': 1 if page_path and page_path.exists() else 0,
        'figures': [],
        'acknowledgements': '',
        'references_excerpt': '',
    }
    (Path(out_dir) / 'metadata.json').write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False)
    )
    _write_readme(out_dir, metadata)
    return metadata


def _find_chrome() -> Optional[str]:
    for c in ('chromium', 'chromium-browser', 'google-chrome', 'chrome'):
        try:
            r = subprocess.run(['which', c], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except FileNotFoundError:
            continue
    return None


def _write_readme(out_dir, metadata):
    src = metadata.get('source_path', '?')
    title = metadata.get('title', '(no title)')
    pages = metadata.get('page_count', 0)
    figs = len(metadata.get('figures', []))
    md = f"""# Source Document — {title or 'untitled'}

Origin: `{src}`
Pages extracted: {pages}
Figures extracted: {figs}

## Files

- `metadata.json` — structured metadata + extracted text excerpts
- `page_NNN.png` — rasterized full-page images at 150 DPI
- `figures/fig-NNN.png` — embedded images extracted from the PDF (raw, may
  include logos / boilerplate; curate before inserting into video)

## Storyboard usage

To insert a source page into the video, add a shot with engine="image":

```json
{{
  "id": "intro_paper",
  "render": {{
    "engine": "image",
    "src": "assets/source_docs/<doc_id>/page_001.png",
    "caption": "{title or 'source document'}",
    "duration_mode": "narration"
  }},
  "narration": "..."
}}
```

The video will display the page with a fade-in, hold for narration duration,
fade-out. See `references/IMAGE_SHOT_ENGINE.md` for full options.
"""
    (Path(out_dir) / 'SOURCE_DOC_README.md').write_text(md)


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='Extract pages, figures, and metadata from a source PDF or URL.'
    )
    ap.add_argument('source', help='path to PDF or URL')
    ap.add_argument('--out', required=True, help='output directory')
    ap.add_argument('--dpi', type=int, default=150)
    ap.add_argument('--no-figures', action='store_true')
    args = ap.parse_args()

    if args.source.startswith('http://') or args.source.startswith('https://'):
        meta = ingest_url(args.source, args.out)
    else:
        meta = ingest_pdf(args.source, args.out, dpi=args.dpi,
                          extract_figures=not args.no_figures)
    print(json.dumps({k: v for k, v in meta.items() if k != 'pdfinfo'}, indent=2))


if __name__ == '__main__':
    main()
