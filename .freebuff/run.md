# Resume Optimizer — Preview Setup

## Architecture

This is a **PySide6 (Qt) desktop application** — a pure native GUI app with no
web server, no HTTP routes, and no HTML templates.  The sole entry point
`main.py` creates a `QApplication` and opens a `QMainWindow`.

## Why not a live app preview

A Qt desktop app requires a **display server** (X11, Wayland, or Windows Desktop
Window Manager).  The Freebuff Preview tab can only display web content (HTTP
URLs or standalone HTML files), and there is no practical way to bridge a Qt GUI
into a browser tab.

## What's available instead

The file `project-dashboard.html` in this directory is a **standalone HTML
project dashboard** that displays the project's architecture, feature list,
file tree, and current git status.  It is served as a static file for the
Preview tab:
- Run: `register_preview` with the absolute path to the HTML file.
- No server, build step, or dependency needed.

## How to reproduce artifacts

1. This HTML dashboard is self-contained (no external assets — everything is
   inlined).  No reproduction steps are needed.
2. If the dashboard needs updating, edit `.freebuff/project-dashboard.html`
   directly.

## How to run the preview

```bash
# No server needed — register the HTML file directly as a static preview:
register_preview htmlPath=C:\Users\user\Desktop\resume-optimimer\.freebuff\project-dashboard.html
```
