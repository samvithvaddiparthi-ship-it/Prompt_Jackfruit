"""Render PAPER.md to a readable single-column A4 HTML (reading copy, not the submission)."""
import markdown
src = open("PAPER.md", encoding="utf-8").read()
head, rest = src.split("\n---\n", 1)
lines = [l for l in head.strip().splitlines() if l.strip()]
title, authors, affil = lines[0].lstrip("# ").strip(), lines[1].strip(), "<br>".join(l.strip() for l in lines[2:])
body = markdown.Markdown(extensions=["tables","fenced_code","attr_list","sane_lists"]).convert(rest)
body = body.replace("<hr />", '<div class="rule"></div>')
CSS = """
@page { size: A4; margin: 19mm 18mm 20mm 18mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family:"Times New Roman",Times,serif; font-size:10.5pt; line-height:1.45; color:#111;
       margin:0; text-align:justify; hyphens:auto; }
.title-block { text-align:center; margin:0 0 18pt; }
h1.paper-title { font-size:17pt; line-height:1.25; margin:0 0 11pt; font-weight:700; text-align:center; hyphens:none; }
.authors { font-size:11pt; margin:0 0 5pt; }
.affil { font-size:9.5pt; font-style:italic; color:#333; line-height:1.4; }
.rule { border-top:0.6pt solid #999; margin:13pt 0; }
h2 { font-size:12pt; margin:15pt 0 6pt; font-weight:700; page-break-after:avoid; text-align:left; hyphens:none; }
h3 { font-size:10.8pt; margin:11pt 0 4pt; font-weight:700; font-style:italic; page-break-after:avoid; text-align:left; hyphens:none; }
p { margin:0 0 7pt; orphans:3; widows:3; }
table { border-collapse:collapse; width:100%; margin:9pt 0 11pt; font-size:8.3pt;
        page-break-inside:avoid; font-family:Helvetica,Arial,sans-serif; text-align:left; }
th,td { border:0.5pt solid #b8b8b8; padding:3.2pt 5pt; vertical-align:top; hyphens:none; }
th { background:#eceff3; font-weight:700; }
tbody tr:nth-child(even) td { background:#f8f9fb; }
blockquote { margin:7pt 0 9pt; padding:6pt 11pt; border-left:2pt solid #99a; background:#f6f7f9;
             font-size:9.6pt; page-break-inside:avoid; }
blockquote p { margin:0 0 4pt; } blockquote p:last-child { margin:0; }
code { font-family:"SF Mono",Menlo,Consolas,monospace; font-size:8.9pt; background:#f0f1f4;
       padding:0.5pt 1pt; border-radius:2px; hyphens:none; -webkit-hyphens:none; word-break:normal; }
pre { background:#f4f5f7; border:0.5pt solid #d8dade; border-radius:3px; padding:7pt 10pt;
      margin:8pt 0; page-break-inside:avoid; text-align:left; }
pre code { background:none; padding:0; font-size:9.2pt; }
ol,ul { margin:0 0 8pt; padding-left:17pt; } li { margin-bottom:3.5pt; }
a { color:#111; text-decoration:none; }
h2 + .rule, .rule + .rule { display:none; }
"""
open("PAPER.html","w",encoding="utf-8").write(
f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head><body>
<div class="title-block"><h1 class="paper-title">{title}</h1>
<div class="authors">{authors.replace('**','')}</div><div class="affil">{affil}</div></div>
<div class="rule"></div>{body}</body></html>""")
print("PAPER.html written")
