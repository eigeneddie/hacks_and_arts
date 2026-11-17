"""
Copies your Substack posts onto the site.

What it does, step by step:
  1. Download the Substack RSS feed (a machine-readable list of recent
     posts, including the full text of free posts).
  2. Merge them into posts.json, the site's own record of every post.
     Substack's feed only lists the ~20 most recent posts, so keeping our
     own record means older posts never disappear from the site.
  3. Write one page per post into posts/<post-name>.html, using the
     site's header, footer and styling.
  4. Put the newest posts on the home page (index.html, between the
     POSTS:START and POSTS:END markers), shown directly with long ones cut
     short and a "Continue reading" link. Older posts go on extra pages:
     page/2.html, page/3.html, ... linked with "Older posts" buttons.

GitHub runs this automatically (see .github/workflows/update-posts.yml).
You can also run it yourself:   python scripts/update_posts.py

Uses only Python's standard library, so there's nothing to install.
"""

import html
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

FEED_URL = "https://edgarsutawika.substack.com/feed"

# Post URLs to leave off the site. Substack creates a "Coming soon"
# placeholder post for every new publication, so it's skipped by default.
# Add a post's URL here to hide it. Its page gets deleted on the next run.
SKIP = {
    "https://edgarsutawika.substack.com/p/coming-soon",
}

# ── Settings for the home page ──
POSTS_PER_PAGE = 5     # how many posts per page before "Older posts"
EXCERPT_LENGTH = 1200  # roughly how many characters of a post to show
                       # before cutting it off with "Continue reading".
                       # Each image counts as 300 characters.

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
POSTS_DIR = ROOT / "posts"
PAGES_DIR = ROOT / "page"
RECORD = ROOT / "posts.json"
START = "<!-- POSTS:START -->"
END = "<!-- POSTS:END -->"

# XML namespace for the <content:encoded> tag, which holds the full post
NS = {"content": "http://purl.org/rss/1.0/modules/content/"}


# ── 1. Read the feed ───────────────────────────────────────────────────

def fetch_feed(url):
    # Substack's bot filter rejects requests that don't look like a normal
    # browser, especially from GitHub's servers. These headers are what a
    # regular Chrome sends when it opens a feed.
    req = urllib.request.Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
        "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
        "Accept-Language": "en-US,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as err:
        if err.code == 403:
            sys.exit("Substack refused the request (403 Forbidden). It's blocking "
                     "this machine, not a bug in the script. Running "
                     "python scripts/update_posts.py on your own PC still works.")
        raise


def parse_feed(xml_bytes):
    posts = []
    for item in ET.fromstring(xml_bytes).iter("item"):
        url = (item.findtext("link") or "").strip()
        if not url:
            continue
        posts.append({
            "url": url,
            # The post's name from its URL: .../p/my-post -> my-post
            "slug": url.rstrip("/").rsplit("/", 1)[-1],
            # Substack sometimes double-encodes characters (&#39; for ').
            # html.unescape turns those back into normal text.
            "title": html.unescape(item.findtext("title") or "Untitled").strip(),
            "summary": html.unescape(item.findtext("description") or "").strip(),
            "date": parsedate_to_datetime(item.findtext("pubDate")).strftime("%Y-%m-%d"),
            "body": item.findtext("content:encoded", default="", namespaces=NS),
        })
    return posts


# ── 2. Keep our own record ─────────────────────────────────────────────

def merge(feed_posts):
    record = json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else []
    by_url = {p["url"]: p for p in record}
    for p in feed_posts:
        by_url[p["url"]] = p  # new posts get added, edited posts get updated
    posts = [p for p in by_url.values() if p["url"] not in SKIP]
    posts.sort(key=lambda p: p["date"], reverse=True)  # newest first
    return posts


# ── Shared page template ───────────────────────────────────────────────

def escaped(p):
    # html.escape makes characters like < & " safe to put inside HTML
    return {k: html.escape(v) for k, v in p.items() if k != "body"}


def page_shell(title, content, prefix, head_extra=""):
    # The header and footer every generated page shares.
    # prefix is "../" for pages one folder down (posts/, page/), so their
    # links to the rest of the site go up one folder first.
    return f"""<!doctype html>
<!-- This page was generated by scripts/update_posts.py.
     Don't edit it by hand: it gets overwritten on the next update. -->
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>{head_extra}
  <link rel="stylesheet" href="{prefix}style.css" />
</head>
<body>

  <header>
    <a class="logo" href="{prefix}index.html">eigeneddie<span>::</span>studios</a>
    <nav>
      <a href="{prefix}index.html">home</a>
      <a href="{prefix}about.html">about</a>
    </nav>
  </header>

{content}

  <footer>
    <span>&copy; 2026 Edgar Sutawika</span>
  </footer>

</body>
</html>
"""


# ── 3. One page per post ───────────────────────────────────────────────

def clean_body(body):
    # Remove any <script> tags from the post. The site shouldn't run
    # code it got from somewhere else.
    return re.sub(r"<script\b.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)


def render_post_page(p):
    e = escaped(p)
    summary = f'\n      <p class="article-summary">{e["summary"]}</p>' if e["summary"] else ""
    head_extra = f"""
  <meta name="description" content="{e["summary"]}" />
  <link rel="canonical" href="{e["url"]}" />
  <!-- canonical tells search engines the Substack version is the original,
       so having the same post in two places doesn't hurt either one -->"""
    content = f"""  <article>
    <div class="article-head">
      <span class="post-date">{e["date"]}</span>
      <h1>{e["title"]}</h1>{summary}
    </div>

    <div class="article-body">
{clean_body(p["body"])}
    </div>

    <p class="article-foot">
      Originally published on <a href="{e["url"]}">Substack</a>.
      Comment, like or subscribe there.
    </p>
  </article>"""
    return page_shell(f'{e["title"]} — eigeneddie::studios', content, "../", head_extra)


def write_post_pages(posts):
    POSTS_DIR.mkdir(exist_ok=True)
    keep = set()
    for p in posts:
        path = POSTS_DIR / f'{p["slug"]}.html'
        path.write_text(render_post_page(p), encoding="utf-8", newline="\n")
        # newline="\n" keeps line endings the same on Windows and on
        # GitHub's Linux machines, so files don't show fake changes
        keep.add(path.name)
    # Delete pages for posts that were removed or added to SKIP
    for old in POSTS_DIR.glob("*.html"):
        if old.name not in keep:
            old.unlink()


# ── 4. Excerpts: cutting long posts short ──────────────────────────────

# Tags that never have a closing tag
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "source", "track", "wbr"}


class TopLevelBlocks(HTMLParser):
    """Splits a post's HTML into its top-level pieces: each paragraph,
    heading, image, list, etc. Cutting a post between pieces (never in
    the middle of one) keeps the HTML valid."""

    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", source)]
        self.depth = 0      # how many tags deep we are right now
        self.start = None   # where the current top-level piece began
        self.blocks = []

    def position(self):
        # The parser reports (line, column); convert to a character index
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            self.handle_startendtag(tag, attrs)
            return
        if self.depth == 0:
            self.start = self.position()
        self.depth += 1

    def handle_startendtag(self, tag, attrs):
        if self.depth == 0:  # a lone <hr> or <img> between paragraphs
            s = self.position()
            self.blocks.append(self.source[s:s + len(self.get_starttag_text())])

    def handle_endtag(self, tag):
        if tag in VOID_TAGS or self.depth == 0:
            return
        self.depth -= 1
        if self.depth == 0:
            end = self.source.index(">", self.position()) + 1
            self.blocks.append(self.source[self.start:end])

    def split(self):
        self.feed(self.source)
        self.close()
        if self.depth > 0 and self.start is not None:  # unclosed last piece
            self.blocks.append(self.source[self.start:])
        return self.blocks


def weight(block):
    # Roughly how much space a piece takes up: its text length, plus a
    # fixed amount per image
    text = html.unescape(re.sub(r"<[^>]+>", "", block)).strip()
    return len(text) + 300 * block.count("<img")


def make_excerpt(body):
    """Returns (excerpt_html, was_cut_short)."""
    blocks = TopLevelBlocks(body).split()
    if not blocks:
        return body, False
    kept, total, has_text = [], 0, False
    for block in blocks:
        w = weight(block)
        # Stop before a piece that would go over the limit, but always
        # show at least one piece of actual text (not just an image)
        if has_text and total + w > EXCERPT_LENGTH:
            break
        kept.append(block)
        total += w
        has_text = has_text or w > 300 * block.count("<img")
    rest = blocks[len(kept):]
    cut = any(weight(b) > 0 for b in rest)  # only "cut" if real content is left
    return "\n".join(kept if cut else blocks), cut


# ── 5. The home page and older-post pages ──────────────────────────────

def render_entry(p, prefix):
    # One post as it appears on the home page: date, title, then the
    # start of the post itself
    e = escaped(p)
    link = f'{prefix}posts/{e["slug"]}.html'
    excerpt, cut = make_excerpt(clean_body(p["body"]))
    summary = f'\n  <p class="entry-summary">{e["summary"]}</p>' if e["summary"] else ""
    more = f'\n  <a class="more" href="{link}">Continue reading &rarr;</a>' if cut else ""
    return f"""<article class="entry">
  <span class="post-date">{e["date"]}</span>
  <h2 class="entry-title"><a href="{link}">{e["title"]}</a></h2>{summary}
  <div class="article-body">
{excerpt}
  </div>{more}
</article>"""


def page_link(n, prefix):
    # Page 1 is the home page; the rest live in page/
    return f"{prefix}index.html" if n == 1 else f"{prefix}page/{n}.html"


def render_pager(n, total, prefix):
    # "← Newer posts   page 2 of 3   Older posts →"
    if total == 1:
        return ""
    newer = f'<a href="{page_link(n - 1, prefix)}">&larr; Newer posts</a>' if n > 1 else "<span></span>"
    older = f'<a href="{page_link(n + 1, prefix)}">Older posts &rarr;</a>' if n < total else "<span></span>"
    return f"""<div class="pager">
  {newer}
  <span class="pager-count">page {n} of {total}</span>
  {older}
</div>"""


def render_page_posts(chunk, n, total, prefix):
    if not chunk:
        return '<p class="empty">First post coming soon.</p>'
    entries = "\n\n".join(render_entry(p, prefix) for p in chunk)
    pager = render_pager(n, total, prefix)
    return entries + ("\n\n" + pager if pager else "")


def write_pages(posts):
    chunks = [posts[i:i + POSTS_PER_PAGE] for i in range(0, len(posts), POSTS_PER_PAGE)] or [[]]
    total = len(chunks)

    # Page 1: the home page, between the markers
    page = INDEX.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(page):
        sys.exit(f"Couldn't find the {START} / {END} markers in index.html")
    new_block = f"{START}\n{render_page_posts(chunks[0], 1, total, '')}\n    {END}"
    INDEX.write_text(pattern.sub(lambda _: new_block, page, count=1), encoding="utf-8", newline="\n")

    # Pages 2, 3, ...: separate files in page/
    keep = set()
    for n in range(2, total + 1):
        PAGES_DIR.mkdir(exist_ok=True)
        content = (f'  <section>\n<p class="section-label">Posts &middot; page {n}</p>\n\n'
                   f'{render_page_posts(chunks[n - 1], n, total, "../")}\n  </section>')
        path = PAGES_DIR / f"{n}.html"
        path.write_text(page_shell(f"Page {n} — eigeneddie::studios", content, "../"),
                        encoding="utf-8", newline="\n")
        keep.add(path.name)
    # Delete pages that aren't needed anymore
    if PAGES_DIR.exists():
        for old in PAGES_DIR.glob("*.html"):
            if old.name not in keep:
                old.unlink()


def main():
    posts = merge(parse_feed(fetch_feed(FEED_URL)))
    RECORD.write_text(json.dumps(posts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    write_post_pages(posts)
    write_pages(posts)
    print(f"{len(posts)} posts on the site.")


if __name__ == "__main__":
    main()
