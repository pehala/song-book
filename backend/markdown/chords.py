from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagPattern, SimpleTextInlineProcessor, SimpleTagInlineProcessor

CHORD_RE = r'({)(.*?)}'


class ChordsExtension(Extension):
    def extendMarkdown(self, md, md_global):
        # Insert del pattern into markdown parser
        md.inlinePatterns.register(ChordPattern(CHORD_RE), "chord", 175)


class ChordPattern(SimpleTagInlineProcessor):
    def __init__(self, pattern):
        super().__init__(pattern, "span")

    def handleMatch(self, m, data):
        tag, start, end = super().handleMatch(m, data)
        tag.set("class", "chord")
        # tag.text.replace("#", "♯")
        # tag.text.replace("b", "♭")
        return tag, start, end

