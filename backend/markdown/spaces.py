from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor

SPACES_RE = r'(\/)(\d+)\/'


class SpacesExtension(Extension):
    def extendMarkdown(self, md, md_global):
        md.inlinePatterns.register(SpacesPattern(SPACES_RE), "spaces", 200)


class SpacesPattern(SimpleTagInlineProcessor):
    def __init__(self, pattern):
        super().__init__(pattern, "span")

    def handleMatch(self, m, data):
        tag, start, end = super().handleMatch(m, data)
        tag.set("class", "spaces")
        count = int(tag.text)
        txt = ""
        for i in range(count):
            txt += "&nbsp;"
        tag.text = txt
        return tag, start, end