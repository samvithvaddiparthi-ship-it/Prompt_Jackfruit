# Paper build

`PAPER.md` is the source of truth. Both PDFs are rendered from it with Chrome's print engine.

```bash
pip install markdown
python paper/render_ieee.py          # -> PAPER_IEEE.html   (IEEE two-column, the submission)
python paper/render_singlecolumn.py  # -> PAPER.html        (single-column reading copy)

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --no-pdf-header-footer --print-to-pdf=PAPER_IEEE.pdf "file://$PWD/PAPER_IEEE.html"
```

Run from the project root (the directory containing `PAPER.md`).
