"""Shared Markdown help dialog utility.

Uses the 'markdown' library if available for full rendering (headings, tables,
code blocks). Falls back to a tiny inline converter for headings / paragraphs
so that the app still shows helpful text without the dependency.
"""
from __future__ import annotations
from pathlib import Path
from typing import Union
import re

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox, QMessageBox, QWidget
)

BASE_CSS = """
<style>
body { font-family: Segoe UI, Arial, sans-serif; font-size: 13px; color: #ddd; background: #1e1e1e; }
h1,h2,h3,h4 { color:#fff; margin-top:14px; }
code { background:#2b2b2b; padding:2px 4px; border-radius:3px; font-size:12px; }
pre code { display:block; padding:8px; overflow:auto; direction:ltr; text-align:left; }
table { border-collapse: collapse; margin:8px 0; }
th, td { border:1px solid #444; padding:4px 8px; }
ul, ol { margin-left:22px; }
a { color:#4fa3ff; text-decoration:none; }
a:hover { text-decoration:underline; }
hr { border:none; border-top:1px solid #444; margin:14px 0; }
/* RTL helper classes applied dynamically */
.rtl body, body.rtl { direction:rtl; }
body.rtl p, body.rtl li, body.rtl td, body.rtl th { text-align:right; }
body.rtl table { direction:rtl; }
</style>
"""

def _fallback_convert(md_text: str) -> str:
    import html
    out = []
    for raw in md_text.splitlines():
        line = raw.rstrip('\n')
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            content = line.lstrip('#').strip()
            tag = f'h{min(level,6)}'
            out.append(f'<{tag}>{html.escape(content)}</{tag}>')
        elif line.strip().startswith(('-', '*')):
            # naive list handling: each bullet becomes its own UL so still readable
            bullet = line.strip()[1:].strip()
            out.append(f'<ul><li>{html.escape(bullet)}</li></ul>')
        elif line.strip():
            out.append(f'<p>{html.escape(line)}</p>')
        else:
            out.append('<br/>')
    return '\n'.join(out)

def _render_markdown(md_text: str) -> str:
    try:
        import markdown  # type: ignore
        return markdown.markdown(md_text, extensions=['fenced_code', 'tables'])
    except Exception:
        return _fallback_convert(md_text)

def show_markdown_dialog(parent: QWidget, path: Union[str, Path], title: str,
                          width: int = 760, height: int = 640) -> None:
    p = Path(path)
    if not p.exists():
        QMessageBox.information(parent, 'Info', f'לא נמצא: {p}')
        return
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        QMessageBox.critical(parent, 'Error', f'כשל בקריאת קובץ: {e}')
        return
    rendered = _render_markdown(text)
    # Detect Hebrew characters to enable RTL layout automatically
    if re.search('[\u0590-\u05FF]', text):
        body_tag_open = '<body dir="rtl" class="rtl" style="text-align:right;">'
    else:
        body_tag_open = '<body>'
    html = BASE_CSS + body_tag_open + rendered + '</body>'
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    v = QVBoxLayout(dlg)
    browser = QTextBrowser()
    browser.setOpenExternalLinks(True)
    browser.setHtml(html)
    v.addWidget(browser)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    bb.rejected.connect(dlg.reject); bb.accepted.connect(dlg.accept)
    v.addWidget(bb)
    dlg.resize(width, height)
    dlg.exec()
