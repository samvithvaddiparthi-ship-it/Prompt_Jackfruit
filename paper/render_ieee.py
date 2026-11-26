"""Render PAPER.md in IEEE Conference format (two-column, US Letter)."""
import re, markdown

ROMAN = {1:"I",2:"II",3:"III",4:"IV",5:"V",6:"VI",7:"VII",8:"VIII",9:"IX",10:"X"}
src = open("PAPER.md", encoding="utf-8").read()
head, rest = src.split("\n---\n", 1)

lines = [l for l in head.strip().splitlines() if l.strip()]
title = lines[0].lstrip("# ").strip()

AUTHORS = [("Samvith Vaddiparthi", "PES1UG24AM468"),
           ("Vikas M S", "PES1UG24AM469"),
           ("Jayant M", "PES1UG24AM122")]
AFFIL = ("Department of Computer Science and Engineering (AI &amp; ML)<br>"
         "PES University, Bengaluru, India")

# ---- section numbering: "## 3. Method" -> "III. METHOD"; "### 3.1 X" -> "A. X"
def fix_heading(m):
    hashes, num, rest_ = m.group(1), m.group(2), m.group(3)
    if hashes == "##":
        return f"## {ROMAN.get(int(num), num)}. {rest_.upper()}"
    sub = int(m.group(4))
    return f"### {chr(64+sub)}. {rest_}"

rest = re.sub(r"^(##) (\d+)\. (.+)$", fix_heading, rest, flags=re.M)
rest = re.sub(r"^(###) (\d+)\.(\d+) (.+)$",
              lambda m: f"### {chr(64+int(m.group(3)))}. {m.group(4)}", rest, flags=re.M)
rest = rest.replace("## Abstract", "## ABSTRACT_MARK")
rest = rest.replace("## References", "## REFERENCES")
rest = re.sub(r"^## (Appendix [AB]) — (.+)$",
              lambda m: f"## APPENDIX {m.group(1)[-1]}<br><span class='apptitle'>{m.group(2)}</span>",
              rest, flags=re.M)

md = markdown.Markdown(extensions=["tables", "fenced_code", "attr_list", "sane_lists"])
body = md.convert(rest)
body = body.replace("<hr />", "")
body = body.replace("<h2>ABSTRACT_MARK</h2>", "")

# wide tables (>5 columns) span both columns
def widen(m):
    tbl = m.group(0)
    ncol = tbl.split("</tr>")[0].count("<th")
    return tbl.replace("<table>", '<table class="wide">', 1) if ncol > 5 else tbl
body = re.sub(r"<table>.*?</table>", widen, body, flags=re.S)

IDX = ("prompt injection, large language models, prompt engineering, AI security, "
       "email assistants, prompt optimization, adversarial robustness")
_i = body.find("<h2>")
_abs, body = body[:_i], body[_i:]
body = (f'<div class="abstract">{_abs}</div>\n'
        f'<p class="idx">{IDX}</p>\n' + body)

authors_html = "".join(
    f'<div class="author"><div class="aname">{n}</div>'
    f'<div class="asrn">{s}</div></div>' for n, s in AUTHORS)

CSS = """
@page { size: letter; margin: 0.75in 0.62in 1in 0.62in; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: "Times New Roman", Times, serif; font-size: 10pt; line-height: 1.12;
       margin: 0; text-align: justify; hyphens: auto; color: #000; }
.head { text-align: center; margin-bottom: 11pt; }
h1.ttl { font-size: 22pt; font-weight: 400; line-height: 1.12; margin: 0 0 13pt;
         hyphens: none; text-align: center; }
.authors { display: flex; justify-content: center; gap: 34pt; margin-bottom: 3pt; }
.author { text-align: center; }
.aname { font-size: 11pt; }
.asrn  { font-size: 9.5pt; font-style: italic; }
.affil { font-size: 9.5pt; font-style: italic; line-height: 1.3; margin-top: 2pt; }
.cols { column-count: 2; column-gap: 0.25in; }
h2 { font-size: 10pt; font-weight: 400; font-variant: small-caps; text-align: center;
     margin: 11pt 0 5pt; page-break-after: avoid; break-after: avoid; hyphens: none;
     letter-spacing: 0.2pt; }
h2:first-child { margin-top: 0; }
.apptitle { font-variant: none; font-style: italic; font-size: 9.5pt; }
h3 { font-size: 10pt; font-weight: 400; font-style: italic; text-align: left;
     margin: 8pt 0 3pt; page-break-after: avoid; break-after: avoid; hyphens: none; }
p { margin: 0 0 5pt; text-indent: 10pt; orphans: 2; widows: 2; }
h2 + p, h3 + p, blockquote + p, table + p, pre + p, ul + p, ol + p { text-indent: 0; }
.abstract p { text-indent: 0; font-weight: 700; font-size: 9pt; text-align: justify;
              margin-bottom: 4pt; }
.abstract p:first-child::before { content: "Abstract—"; font-weight: 700; font-style: italic; }
.idx { font-size: 9pt; margin: 0 0 7pt; text-indent: 0; }
.idx::before { content: "Index Terms—"; font-style: italic; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0 7pt; font-size: 7.3pt;
        break-inside: avoid; page-break-inside: avoid; font-family: "Times New Roman", serif;
        text-align: left; }
table.wide { column-span: all; font-size: 7.6pt; margin: 7pt 0 9pt; }
th, td { border: 0.5pt solid #000; padding: 2pt 3.5pt; vertical-align: top; hyphens: none; }
th { font-weight: 700; text-align: left; background: #e9e9e9; }
blockquote { margin: 5pt 0 6pt; padding: 4pt 7pt; border-left: 1.5pt solid #555;
             background: #f2f2f2; font-size: 8.6pt; break-inside: avoid; }
blockquote p { margin: 0 0 3pt; text-indent: 0; } blockquote p:last-child { margin: 0; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.3pt; hyphens: none;
       -webkit-hyphens: none; word-break: normal; }
pre { background: #f2f2f2; border: 0.5pt solid #bbb; padding: 4pt 7pt; margin: 5pt 0;
      break-inside: avoid; text-align: left; }
pre code { font-size: 8.6pt; }
ol, ul { margin: 0 0 5pt; padding-left: 13pt; } li { margin-bottom: 2.5pt; }
h2[id^="references"] + ol, .refs ol { font-size: 8.6pt; }
"""

html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head>
<body>
<div class="head">
  <h1 class="ttl">{title}</h1>
  <div class="authors">{authors_html}</div>
  <div class="affil">{AFFIL}</div>
</div>
<div class="cols">
{body}
</div>
</body></html>"""
open("PAPER_IEEE.html", "w", encoding="utf-8").write(html)
print("PAPER_IEEE.html written")
