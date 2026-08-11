"""HTML cleaning. Collected content is untrusted (spec §47) - we only
ever extract text, never execute scripts or fetch remote resources from it."""

from __future__ import annotations

from bs4 import BeautifulSoup


def strip_html(html: str | None) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
