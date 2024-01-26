"""Markdown extension for paragraphs"""

import re
import string

# because mismatch is too slow, add parsers for paragraph and text

PARAGRAPH = (
    # start with none punctuation, not number, not whitespace
    r"(?:^[^\s\d"
    + re.escape(string.punctuation)
    + r"][^\n]*\n)+"
)

__all__ = ["paragraph"]


# pylint: disable=unused-argument
def parse_paragraph(block, m, state):
    """Parse paragraph"""
    text = m.group(0)
    state.add_paragraph(text)
    return m.end()


def paragraph(md):
    """Increase the speed of parsing paragraph"""
    md.block.register("paragraph", PARAGRAPH, parse_paragraph)
