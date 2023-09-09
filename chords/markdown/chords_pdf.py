"""Markdown Chords extension for PDF generation"""
from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor

CHORD_RE = r"({)(.*?)}"


class ChordsPDFExtension(Extension):
    """Extension for Chords in PDF"""

    def extendMarkdown(self, md):
        """Chords markdown extension for usage in PDF files"""
        # Insert del pattern into markdown parser
        md.inlinePatterns.register(ChordPDFPattern(CHORD_RE), "chord", 175)


class ChordPDFPattern(SimpleTagInlineProcessor):
    """Pattern for ChordsPDFExtension"""

    def __init__(self, pattern):
        super().__init__(pattern, "sup")

    def handleMatch(self, m, data):
        tag, start, end = super().handleMatch(m, data)
        tag.set("class", "chord")
        tag.text += "&nbsp;"
        return tag, start, end
