"""HTML cleaning. Collected content is untrusted (spec §47) - we only
ever extract text, never execute scripts or fetch remote resources from it."""

from __future__ import annotations

import html as html_module

from bs4 import BeautifulSoup


def strip_html(html: str | None) -> str:
    if not html:
        return ""
    # Some ATS APIs (observed: Greenhouse `content`) return HTML that has
    # been entity-escaped an extra time (e.g. "&lt;div&gt;" instead of
    # "<div>"), which would otherwise leave literal tag text in the
    # output instead of being parsed away.
    unescaped = html_module.unescape(html)
    soup = BeautifulSoup(unescaped, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
