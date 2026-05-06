#!/usr/bin/env python3
"""Validate the generated proposal site and its bibliography data."""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlparse

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
PUBLIC = SITE / "public"


def run(cmd: list[str], cwd: Path) -> int:
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd).returncode


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


BASE_URL = load_toml(SITE / "config.toml").get("base_url", "").rstrip("/")


def normalize(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def title_variants(value: str) -> set[str]:
    normalized = normalize(value)
    variants = {normalized}
    for article in ("a ", "an ", "the "):
        if normalized.startswith(article):
            variants.add(normalized[len(article) :])
        else:
            variants.add(article + normalized)
    return variants


def first_title(value: str) -> str | None:
    match = re.search(r'"([^"]+)"', value)
    if not match:
        match = re.search(r"<em>(.*?)</em>", value)
    if not match:
        return None
    return html.unescape(match.group(1)).strip().rstrip(".")


def title_matches(title: str, bibliography_titles: set[str]) -> bool:
    variants = title_variants(title)
    return any(
        variant == candidate
        or variant.startswith(candidate + " ")
        or candidate.startswith(variant + " ")
        for variant in variants
        for candidate in bibliography_titles
    )


def validate_bibliography() -> list[str]:
    errors: list[str] = []
    bibliography = load_toml(SITE / "data" / "bibliography.toml")

    for index, entry in enumerate(bibliography.get("entry", []), start=1):
        text = entry.get("text", "").strip()
        url = entry.get("url", "").strip()
        if not text:
            errors.append(f"bibliography entry {index} has no text")
        if not url:
            errors.append(f"bibliography entry {index} has no url: {text}")
        elif not re.match(r"^https?://", url):
            errors.append(f"bibliography entry {index} has invalid url: {url}")

    return errors


def validate_course_texts() -> list[str]:
    errors: list[str] = []
    bibliography = load_toml(SITE / "data" / "bibliography.toml")
    courses = load_toml(SITE / "data" / "courses.toml")

    bibliography_titles = {
        variant
        for entry in bibliography.get("entry", [])
        for title in [first_title(entry.get("text", ""))]
        if title
        for variant in title_variants(title)
    }

    for course in courses.get("course", []):
        course_name = course.get("title_es") or course.get("slug", "unknown course")
        for text in course.get("texts", []):
            title = first_title(text)
            if not title:
                continue

            if not title_matches(title, bibliography_titles):
                errors.append(f"{course_name}: '{title}' is missing from bibliography")

        for ref in course.get("references", []):
            url = ref.get("url", "").strip()
            if not url or not re.match(r"^https?://", url):
                errors.append(f"{course_name}: invalid reference URL for {ref.get('name', '<unnamed>')}: {url}")

    return errors


def public_path_for_href(href: str, html_file: Path) -> Path | None:
    parsed = urlparse(href)
    base = urlparse(BASE_URL)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != base.scheme or parsed.netloc != base.netloc:
            return None

    path = unquote(parsed.path)
    if not path.endswith(".pdf"):
        return None

    base_path = base.path.rstrip("/")
    if base_path and path.startswith(base_path + "/"):
        path = path[len(base_path) :]

    if path.startswith("/"):
        marker = "/pdf/"
        if marker in path:
            return PUBLIC / path.split(marker, 1)[1].join(["pdf/", ""])
        return PUBLIC / path.lstrip("/")

    return (html_file.parent / path).resolve()


def validate_pdf_links() -> list[str]:
    errors: list[str] = []
    href_pattern = re.compile(r"""href=["']([^"']+\.pdf(?:\?[^"']*)?)["']""")

    html_files = sorted(PUBLIC.rglob("*.html"))
    if not html_files:
        return ["site/public has no generated HTML files"]

    for html_file in html_files:
        for href in href_pattern.findall(html_file.read_text(encoding="utf-8")):
            target = public_path_for_href(href, html_file)
            if target and not target.exists():
                errors.append(f"{html_file.relative_to(REPO)} links to missing PDF: {href}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-zola", action="store_true", help="do not run zola check/build")
    parser.add_argument("--skip-pdf-links", action="store_true", help="do not require built PDF files")
    args = parser.parse_args()

    errors: list[str] = []

    if not args.skip_zola:
        if run(["zola", "check"], SITE) != 0:
            errors.append("zola check failed")
        if run(["zola", "build"], SITE) != 0:
            errors.append("zola build failed")

    errors.extend(validate_bibliography())
    errors.extend(validate_course_texts())
    if not args.skip_pdf_links:
        errors.extend(validate_pdf_links())

    if errors:
        print("\nValidation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("\nValidation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
