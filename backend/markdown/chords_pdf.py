from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor

CHORD_RE = r'({)(.*?)}'


class ChordsPDFExtension(Extension):
    def extendMarkdown(self, md, md_global):
        # Insert del pattern into markdown parser
        md.inlinePatterns.register(ChordPDFPattern(CHORD_RE), "chord", 175)


class ChordPDFPattern(SimpleTagInlineProcessor):
    def __init__(self, pattern):
        super().__init__(pattern, "sup")

    def handleMatch(self, m, data):
        tag, start, end = super().handleMatch(m, data)
        tag.set("class", "chord")
        tag.text += "&nbsp;"
        # tag.text.replace("#", "♯")
        # tag.text.replace("b", "♭")
        return tag, start, end
