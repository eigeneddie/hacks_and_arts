> generated with AI, not reviewed yet

# hacks & arts

Personal site for Edgar Sutawika — a portfolio and field log for hardware projects built with minimal resources.

Live at: [edgarsutawika.com](https://edgarsutawika.com) *(update with actual URL)*

## What it is

A single-page static site with three sections:

- **Projects** — cards for each hardware project with a name, status badge (`IN PROGRESS` / `PLANNED` / `DONE`), description, and tags
- **Field Log** — chronological updates tied to specific projects, newest first
- **Header / Footer** — nav links and contact info

## Stack

Plain HTML + CSS. No framework, no build step, no dependencies.

## Files

```
index.html   — the whole site
style.css    — all styling
previews/    — design explorations from the iteration process
```

## Adding a project

Copy a `<div class="project">` block in `index.html` and fill in the fields. Change the status badge class for different states:

```html
<span class="project-status">IN PROGRESS</span>   <!-- teal -->
<span class="project-status planned">PLANNED</span> <!-- grey -->
<span class="project-status done">DONE</span>       <!-- muted -->
```

## Adding a log entry

Prepend a new `<div class="log-entry">` block inside the Field Log `<section>`. Keep entries newest-first.

```html
<div class="log-entry">
  <div class="log-meta">
    <span class="date">YYYY-MM-DD</span>
    <span>project-slug</span>
  </div>
  <p class="log-title">Short title</p>
  <p class="log-body">Details.</p>
</div>
```

## Deploying

Static files — drop on GitHub Pages, Netlify, Cloudflare Pages, or any host that serves HTML.
