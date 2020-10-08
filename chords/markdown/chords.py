"""Markdown extension for chords"""
from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor

CHORD_RE = r'({)(.*?)}'


class ChordsExtension(Extension):
    """Markdown extension for convert {chord} into chords"""
    def extendMarkdown(self, md):
        # Insert del pattern into markdown parser
        md.inlinePatterns.register(ChordPattern(CHORD_RE), "chord", 175)


class ChordPattern(SimpleTagInlineProcessor):
    """Pattern for ChordsExtension"""
    def __init__(self, pattern):
        super().__init__(pattern, "span")

    def handleMatch(self, m, data):
        tag, start, end = super().handleMatch(m, data)
        tag.set("class", "chord")
        return tag, start, end
