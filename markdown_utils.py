import bleach
import markdown as md

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "b", "i", "a", "ul", "ol", "li",
    "blockquote", "code", "pre", "h1", "h2", "h3", "img"
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title", "width", "height"]
}

COMMENT_ALLOWED_TAGS = [
    "p", "br", "strong", "em", "b", "i", "a", "code"
]

def render_markdown(raw_md, allowed_tags=None):
    tags = allowed_tags or ALLOWED_TAGS
    html = md.markdown(raw_md or "", extensions=["fenced_code"])
    clean_html = bleach.clean(html, tags=tags, attributes=ALLOWED_ATTRS, strip=True)
    return clean_html
