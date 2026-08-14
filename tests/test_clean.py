from __future__ import annotations

from jobintel.normalize.clean import strip_html


def test_strip_html_removes_normal_tags():
    text = strip_html("<div><p>Remote worldwide role.</p></div>")
    assert text == "Remote worldwide role."


def test_strip_html_handles_double_escaped_entities():
    """Regression test: Greenhouse's `content` field was observed
    returning HTML that was entity-escaped an extra time (e.g.
    "&lt;div&gt;" instead of "<div>"). Without unescaping first, the
    literal tag text leaked into job_description_clean instead of being
    stripped, and worse, the real words inside were fine but wrapped in
    junk - this asserts the tags are actually parsed away."""
    doubly_escaped = "&lt;div&gt;&lt;p&gt;Remote worldwide role. Work from anywhere.&lt;/p&gt;&lt;/div&gt;"
    text = strip_html(doubly_escaped)
    assert "<div>" not in text
    assert "<p>" not in text
    assert "Remote worldwide role. Work from anywhere." in text


def test_strip_html_empty_input():
    assert strip_html(None) == ""
    assert strip_html("") == ""
