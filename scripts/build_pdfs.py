#!/usr/bin/env python3
"""
Build PDF exports for every (audience × language) combination.

Output files written to site/public/pdf/:
  full-es.pdf
  full-en.pdf
  students-es.pdf
  students-en.pdf
  faculty-es.pdf
  faculty-en.pdf
  authorities-es.pdf
  authorities-en.pdf

Requires: chromium (provided via the nix dev shell), a running zola build.
The script starts a local HTTP server, drives chromium with ?lang= query
parameter, then shuts the server down.
"""
from __future__ import annotations

import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "site" / "public"
PDF_DIR = PUBLIC / "pdf"
AUDIENCES_TOML = REPO / "site" / "data" / "audiences.toml"
PORT = 8765

LANGS = ["es", "en"]


def load_routes() -> list[tuple[str, str]]:
    """Derive (slug, route) pairs from data/audiences.toml plus the 'full' default."""
    import tomllib
    with AUDIENCES_TOML.open("rb") as f:
        data = tomllib.load(f)
    routes = [("full", "")]
    for entry in data.get("audience", []):
        slug = entry["slug"]
        routes.append((slug, f"{slug}/"))
    return routes


def find_chromium() -> str:
    # Allow override via env (CI uses LSC_BROWSER=chrome)
    forced = os.environ.get("LSC_BROWSER")
    candidates = [forced] if forced else ["chromium", "chromium-browser", "google-chrome", "chrome"]
    for name in candidates:
        if not name:
            continue
        path = shutil.which(name)
        if path:
            return path
    print("ERROR: no chromium-class browser found in PATH.", file=sys.stderr)
    print("Enter the nix dev shell first: `nix develop`, or set LSC_BROWSER.", file=sys.stderr)
    sys.exit(1)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs):  # silence per-request logging
        pass


def serve(directory: Path) -> tuple[socketserver.ThreadingTCPServer, threading.Thread]:
    os.chdir(directory)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), QuietHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, t


def build_pdf(chromium: str, url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        chromium,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=8000",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={output}",
        url + ("&" if "?" in url else "?") + "pdf=1",
    ]
    print(f"  → {output.name}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"    chromium failed: {res.stderr}", file=sys.stderr)


def main() -> int:
    if not PUBLIC.exists() or not (PUBLIC / "index.html").exists():
        print("ERROR: site/public/ not built. Run `make build` first.", file=sys.stderr)
        return 1

    chromium = find_chromium()
    print(f"Using chromium: {chromium}")

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    httpd, _ = serve(PUBLIC)
    print(f"Serving site/public on http://127.0.0.1:{PORT}")
    time.sleep(0.3)

    try:
        for name, route in load_routes():
            for lang in LANGS:
                url = f"http://127.0.0.1:{PORT}/{route}?lang={lang}"
                output = PDF_DIR / f"{name}-{lang}.pdf"
                build_pdf(chromium, url, output)
    finally:
        httpd.shutdown()
        httpd.server_close()

    print(f"\nDone. PDFs written to {PDF_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
