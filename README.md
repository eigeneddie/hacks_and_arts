> generated with AI, not reviewed yet

# eigeneddie::studios

Independent R&D notes by Edgar Sutawika: teardowns, experiments and builds on a budget, documented as I go.

Live at: [eigeneddie.com](https://eigeneddie.com)

## Pages

- **Home** (`index.html`): banner, intro, then the newest posts shown directly (long ones cut short with "Continue reading"). Older posts are on `page/2.html`, `page/3.html`, ... behind an "Older posts" link
- **About** (`about.html`): who I am, what this is, how to reach me

## Stack

Plain HTML + CSS, hosted on GitHub Pages. No framework, no dependencies.

The one exception: the About page text is written in Markdown (`_includes/about.md`, `_includes/author.md`). GitHub Pages runs Jekyll on every push, and Jekyll pastes that text into `about.html`. Because of that, opening `about.html` straight from disk shows the raw Jekyll "include" lines instead of the text. (Don't write Jekyll's curly-brace-percent tags in this README: Jekyll processes it too, and a stray tag breaks the build.) Check the live site, or use VS Code's Markdown preview (Ctrl+Shift+V) on the `.md` file.

## Files

```
index.html         home page (Posts list is auto-filled from Substack)
posts/             full post pages, generated from Substack
page/              older-post pages (2, 3, ...), generated; only exists once there are more than 5 posts
posts.json         record of every post, used to build the above
about.html         about page (layout only)
_includes/         about.md, author.md: the About page text, in Markdown
style.css          all styling, shared by both pages
images/banner.jpg  banner photo (resized for the web, ~190 KB)
scripts/           update_posts.py: pulls posts from Substack into index.html
.github/workflows/ update-posts.yml: runs that script every 6 hours
CNAME              tells GitHub Pages to serve this repo at eigeneddie.com
```

The header and footer are copied in both HTML files. If you change one, change the other.

## Adding a post

Publish on [Substack](https://edgarsutawika.substack.com). That's it.

A GitHub Action (`.github/workflows/update-posts.yml`) runs every 6 hours. It runs `scripts/update_posts.py`, which:

1. reads the Substack feed (including the full text of free posts),
2. merges it into `posts.json`, the site's own record. Substack's feed only lists the ~20 newest posts, so this keeps older ones on the site,
3. writes a full page for each post to `posts/<post-name>.html`,
4. rewrites the list between the `POSTS:START` / `POSTS:END` markers in `index.html`,

then commits if anything changed.

- **Don't want to wait?** GitHub repo → Actions → "Update posts from Substack" → Run workflow.
- **Run it locally:** `python scripts/update_posts.py`
- **Hide a post from the site:** add its URL to `SKIP` in `scripts/update_posts.py`.
- **To edit a post, edit it on Substack.** Don't hand-edit `posts/`, `posts.json` or the list in `index.html`: the next run overwrites them.
- Paid posts only show the free preview, because that's all the feed contains.
- Each post page links back to Substack for comments and subscribing, and tells search engines the Substack version is the original.

## Domain setup

- DNS for `eigeneddie.com` is managed at Wix.
- `eigeneddie.com` needs exactly these four A records (GitHub Pages):
  `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
- `www` is a CNAME to `eigeneddie.github.io`.
- Any other A record (for example Wix's `185.230.63.x`) breaks HTTPS. GitHub can't get a certificate while DNS points somewhere else too.
- In the repo's Settings → Pages: custom domain is `eigeneddie.com`, and Enforce HTTPS is on.

## Deploying

Push to `main`. GitHub Pages republishes in about a minute.
