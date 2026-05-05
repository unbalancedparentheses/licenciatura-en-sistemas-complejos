#!/usr/bin/env python3
"""
Extract structured content from legacy index.html into TOML data files
and HTML section partials. Designed to preserve content byte-for-byte
where reasonable.

Run from repo root:
    python3 scripts/extract.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEGACY = REPO / "index.html"
DATA = REPO / "site" / "data"
SECTIONS = REPO / "site" / "templates" / "sections"


def toml_escape(s: str) -> str:
    """Escape a string for TOML triple-quoted basic string."""
    return s.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def toml_str(s: str) -> str:
    """Emit a TOML basic string literal."""
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[áàä]", "a", s)
    s = re.sub(r"[éèë]", "e", s)
    s = re.sub(r"[íìï]", "i", s)
    s = re.sub(r"[óòö]", "o", s)
    s = re.sub(r"[úùü]", "u", s)
    s = re.sub(r"ñ", "n", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def load() -> str:
    return LEGACY.read_text(encoding="utf-8")


def block_text(start_tag: str, end_tag: str, src: str, start: int = 0) -> tuple[str, int, int]:
    """Find the next block bounded by start_tag and matching end_tag (naive, depth-aware)."""
    s = src.find(start_tag, start)
    if s < 0:
        return "", -1, -1
    depth = 1
    i = s + len(start_tag)
    open_re = re.compile(re.escape(start_tag.split(" ")[0]) if " " in start_tag else re.escape(start_tag))
    return "", -1, -1


# Course extraction --------------------------------------------------------


COURSE_BLOCK_RE = re.compile(
    r'<div class="course">(?P<body>.*?)</div>\s*\n\s*(?=<div class="course">|<h2>|<!-- |<div class="page-break"|</div>\s*\n\s*<!-- )',
    re.DOTALL,
)
TITLE_ES_RE = re.compile(r'<div class="course-title-es">(.*?)</div>', re.DOTALL)
TITLE_EN_RE = re.compile(r'<div class="course-title-en">(.*?)</div>', re.DOTALL)
SECTION_LABEL_RE = re.compile(r'<div class="course-section-label">(.*?)</div>', re.DOTALL)
EVAL_PRIMARY_RE = re.compile(r'<span class="eval-badge">(.*?)</span>', re.DOTALL)
EVAL_SECONDARY_RE = re.compile(r'<span class="eval-secondary">(.*?)</span>', re.DOTALL)
LANG_ES_RE = re.compile(r'<p class="lang-es">(.*?)</p>', re.DOTALL)
LANG_EN_RE = re.compile(r'<p class="lang-en">(.*?)</p>', re.DOTALL)
LI_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL)


def split_courses_by_year(html: str) -> list[tuple[str, str]]:
    """
    Yield (year_marker, course_block_html) tuples in document order.
    year_marker is '1', '2', '3', or '3.5'.
    """
    # Find each course block and the most recent <h2>Año X — ...</h2> heading before it.
    year_iter = list(re.finditer(r"<h2>A[ñn]o ([0-9.]+) — ([^<]+)</h2>", html))
    course_iter = list(re.finditer(r'<div class="course">', html))
    results: list[tuple[str, int]] = []
    for cm in course_iter:
        # Find the most recent year heading before this course start.
        year = None
        for ym in year_iter:
            if ym.start() < cm.start():
                year = ym.group(1)
            else:
                break
        if year is None:
            continue
        results.append((year, cm.start()))
    return results


def find_course_end(html: str, start: int) -> int:
    """Find the matching </div> for the <div class="course"> opening at start.
    The course block can contain nested <div class="bilingual-block"> etc., so
    we have to balance <div ...>...</div>."""
    i = start
    open_re = re.compile(r"<div\b", re.IGNORECASE)
    close_re = re.compile(r"</div>", re.IGNORECASE)
    depth = 0
    pos = start
    while pos < len(html):
        m_open = open_re.search(html, pos)
        m_close = close_re.search(html, pos)
        if not m_close:
            return -1
        if m_open and m_open.start() < m_close.start():
            depth += 1
            pos = m_open.end()
        else:
            depth -= 1
            pos = m_close.end()
            if depth == 0:
                return pos
    return -1


def extract_section(html: str, label: str, after: int) -> str | None:
    """Return the HTML block between a section label and the next section label or end."""
    pattern = re.compile(
        r'<div class="course-section-label">' + re.escape(label) + r"[^<]*</div>(.*?)(?=<div class=\"course-section-label\"|</div>\s*$)",
        re.DOTALL,
    )
    m = pattern.search(html, after)
    if not m:
        return None
    return m.group(1).strip()


def extract_lis(html_fragment: str) -> list[str]:
    return [li.group(1).strip() for li in LI_RE.finditer(html_fragment)]


def extract_lang_pair(html_fragment: str) -> tuple[str, str]:
    es = LANG_ES_RE.search(html_fragment)
    en = LANG_EN_RE.search(html_fragment)
    return (es.group(1).strip() if es else "", en.group(1).strip() if en else "")


def extract_evaluation(html_fragment: str) -> tuple[str, list[str]]:
    p = EVAL_PRIMARY_RE.search(html_fragment)
    secondaries = [m.group(1).strip() for m in EVAL_SECONDARY_RE.finditer(html_fragment)]
    return (p.group(1).strip() if p else "", secondaries)


def parse_li_for_text(li: str) -> str:
    """Convert a course bibliography <li> to a TOML-ready string.
    Preserves <em>, <a> as inline HTML so the template can render literally."""
    return li.strip()


def parse_li_for_reference(li: str) -> dict:
    """Reference courses items have either '<a href="X">name</a>' or 'Name — <a href="X">domain</a>' or plain text."""
    a_match = re.search(r'<a href="([^"]+)">([^<]+)</a>', li)
    text = li.strip()
    if a_match:
        url = a_match.group(1)
        # Use full text (with — domain) as label, but if it has the form 'Name — link', strip.
        label = re.sub(r'\s*<a href="[^"]+">.*?</a>\s*', "", li).strip()
        # Trim trailing em-dash if present
        label = re.sub(r"\s*—\s*$", "", label).strip()
        if not label:
            label = a_match.group(2).strip()
        return {"name": label, "url": url}
    return {"name": text, "url": ""}


def extract_courses(html: str) -> list[dict]:
    courses = []
    starts = split_courses_by_year(html)
    for year, start in starts:
        end = find_course_end(html, start)
        if end < 0:
            print(f"WARN: cannot find end of course at {start}", file=sys.stderr)
            continue
        block = html[start:end]
        # Title
        t_es = TITLE_ES_RE.search(block)
        t_en = TITLE_EN_RE.search(block)
        if not t_es:
            continue
        title_es = t_es.group(1).strip()
        title_en = t_en.group(1).strip() if t_en else ""

        # Sections
        obj_block = extract_section_named(block, ["Objetivo / Objective"])
        cnt_block = extract_section_named(block, ["Contenido / Content"])
        texts_block = extract_section_named(block, ["Textos principales / Primary texts"])
        refs_block = extract_section_named(block, ["Cursos de referencia / Reference courses"])
        eval_block = extract_section_named(block, ["Evaluación / Evaluation"])

        # Capture any non-standard sections (e.g., the cultural canon list).
        known_labels = {
            "Objetivo / Objective", "Contenido / Content",
            "Textos principales / Primary texts",
            "Cursos de referencia / Reference courses",
            "Evaluación / Evaluation",
        }
        extras: list[tuple[str, str]] = []
        for sm in re.finditer(r'<div class="course-section-label">\s*([^<]+?)\s*</div>', block):
            label = sm.group(1).strip()
            if label in known_labels:
                continue
            start = sm.end()
            next_label = re.search(r'<div class="course-section-label">', block[start:])
            end = start + next_label.start() if next_label else len(block)
            extras.append((label, block[start:end].strip()))

        obj_es, obj_en = extract_lang_pair(obj_block) if obj_block else ("", "")
        cnt_es, cnt_en = extract_lang_pair(cnt_block) if cnt_block else ("", "")
        texts = extract_lis(texts_block) if texts_block else []
        refs_raw = extract_lis(refs_block) if refs_block else []
        refs = [parse_li_for_reference(r) for r in refs_raw]
        eval_p, eval_secondaries = extract_evaluation(eval_block) if eval_block else ("", [])

        # notes — italic <em> paragraph immediately before evaluation, if any
        notes = ""
        notes_match = re.search(r"<p><em>(.*?)</em></p>", block, re.DOTALL)
        if notes_match:
            notes = notes_match.group(1).strip()

        courses.append({
            "slug": slugify(title_es),
            "title_es": title_es,
            "title_en": title_en,
            "year": float(year) if "." in year else int(year),
            "objective_es": obj_es,
            "objective_en": obj_en,
            "content_es": cnt_es,
            "content_en": cnt_en,
            "notes_html": notes,
            "texts": texts,
            "references": refs,
            "evaluation_primary": eval_p,
            "evaluation_secondaries": eval_secondaries,
            "extras": extras,
        })
    return courses


def extract_section_named(block: str, labels: list[str]) -> str | None:
    """Find a course-section-label whose text matches any of `labels` and return
    the HTML up to the next course-section-label or end of block."""
    label_re = re.compile(
        r'<div class="course-section-label">\s*('
        + "|".join(re.escape(l) for l in labels)
        + r")\s*</div>"
    )
    m = label_re.search(block)
    if not m:
        return None
    start = m.end()
    next_label = re.search(r'<div class="course-section-label">', block[start:])
    end = start + next_label.start() if next_label else len(block)
    return block[start:end]


# Curriculum block lookup --------------------------------------------------


def lookup_curriculum(html: str, courses: list[dict]) -> None:
    """Read the §8.2 curriculum table and assign block + position to each course."""
    # Find the year-header rows
    grid_re = re.compile(r"<h3>A[ñn]o ([0-9.]+) — [^<]+</h3>\s*<table>(.*?)</table>", re.DOTALL)
    by_title: dict[str, dict] = {}
    for c in courses:
        by_title[c["title_es"].lower()] = c

    for m in grid_re.finditer(html):
        year = m.group(1)
        table = m.group(2)
        # Header row
        rows = re.findall(r"<tr>(.*?)</tr>", table, re.DOTALL)
        if not rows:
            continue
        header = rows[0]
        cols = [td.group(1).strip() for td in re.finditer(r"<th>(.*?)</th>", header)]
        # cols are like ["Bloque A","Bloque B","Bloque C","Bloque D"]
        block_letters = []
        for c in cols:
            mb = re.search(r"Bloque ([A-D])", c)
            if mb:
                block_letters.append(mb.group(1))
        # Subsequent rows hold courses in order
        position = 0
        for r in rows[1:]:
            tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.DOTALL)
            if any("Studio" in t or "Studio " in t for t in tds):
                continue
            position += 1
            for idx, t in enumerate(tds):
                title = re.sub(r"<[^>]+>", "", t).strip()
                if not title:
                    continue
                key = title.lower()
                if key in by_title:
                    by_title[key]["block"] = block_letters[idx] if idx < len(block_letters) else ""
                    by_title[key]["position"] = position


# TOML emission ------------------------------------------------------------


def emit_courses(courses: list[dict]) -> str:
    out = ['# Auto-extracted from legacy index.html. See scripts/extract.py.', "", ]
    for c in courses:
        out.append("[[course]]")
        out.append(f'slug = "{c["slug"]}"')
        out.append(f"title_es = {toml_str(c['title_es'])}")
        out.append(f"title_en = {toml_str(c['title_en'])}")
        if isinstance(c["year"], float):
            out.append(f'year = {c["year"]}')
        else:
            out.append(f'year = {c["year"]}')
        out.append(f'block = "{c.get("block","")}"')
        out.append(f'position = {c.get("position",0)}')
        out.append('audiences = ["students", "faculty", "authorities"]')
        out.append(f"objective_es = {toml_str(c['objective_es'])}")
        out.append(f"objective_en = {toml_str(c['objective_en'])}")
        out.append(f"content_es = {toml_str(c['content_es'])}")
        out.append(f"content_en = {toml_str(c['content_en'])}")
        if c.get("notes_html"):
            out.append(f"notes_html = {toml_str(c['notes_html'])}")
        # texts
        if c["texts"]:
            out.append("texts = [")
            for t in c["texts"]:
                out.append(f"  {toml_str(t)},")
            out.append("]")
        else:
            out.append("texts = []")
        # references
        if c["references"]:
            out.append("references = [")
            for r in c["references"]:
                out.append(f'  {{ name = {toml_str(r["name"])}, url = {toml_str(r["url"])} }},')
            out.append("]")
        else:
            out.append("references = []")
        out.append(f"evaluation_primary = {toml_str(c['evaluation_primary'])}")
        if c.get('evaluation_secondaries'):
            out.append("evaluation_secondaries = [")
            for s in c['evaluation_secondaries']:
                out.append(f"  {toml_str(s)},")
            out.append("]")
        else:
            out.append("evaluation_secondaries = []")
        # extras must come AFTER all primary fields because they open a sub-table
        if c.get("extras"):
            for label, body in c["extras"]:
                out.append("")
                out.append("[[course.extra_section]]")
                out.append(f"label = {toml_str(label)}")
                out.append('html = """')
                out.append(toml_escape(body))
                out.append('"""')
        out.append("")
    return "\n".join(out)


# Studio extraction --------------------------------------------------------


def extract_studios(html: str) -> list[dict]:
    studios = []
    # Restrict to §10 Studio Descriptions (the canonical block).
    s = html.find("<h1>Studio Descriptions</h1>")
    e = html.find("<h1>Admissions</h1>", s)
    if s < 0 or e < 0:
        return []
    region = html[s:e]
    pos = 0
    while True:
        sm = re.search(r'<div class="studio">', region[pos:])
        if not sm:
            break
        start = pos + sm.start()
        end = find_course_end(region, start)  # depth-balanced div matching
        if end < 0:
            break
        block = region[start:end]
        pos = end
        num_match = re.search(r'<div class="studio-number">([^<]+)</div>', block)
        title_match = re.search(r'<div class="studio-title">([^<]+)</div>', block)
        if not num_match or not title_match:
            continue
        # Title can be "Escritura y Oratoria / Writing and Rhetoric" or just one
        title_full = title_match.group(1).strip()
        if " / " in title_full:
            title_es, title_en = [t.strip() for t in title_full.split(" / ", 1)]
        else:
            title_es = title_en = title_full

        # Number text like "Studio I — Año 1, Bloques A+B" or just "Studio I"
        num_text = num_match.group(1).strip()
        rn = re.search(r"Studio ([IVX]+)", num_text)
        roman = rn.group(1) if rn else ""

        body = block[block.find("</div>", title_match.end()) + 6:]
        # extract h4 subsections
        sections: dict[str, str] = {}
        for sm in re.finditer(r"<h4>([^<]+)</h4>\s*(.*?)(?=<h4>|$)", body, re.DOTALL):
            sections[sm.group(1).strip()] = sm.group(2).strip()

        studios.append({
            "number_text": num_text,
            "roman": roman,
            "title_es": title_es,
            "title_en": title_en,
            "raw_html": block.strip(),
            "sections": sections,
        })
    return studios


def emit_studios(studios: list[dict]) -> str:
    out = ['# Auto-extracted from legacy index.html. See scripts/extract.py.', "", ]
    for s in studios:
        out.append("[[studio]]")
        out.append(f"number_text = {toml_str(s['number_text'])}")
        out.append(f"roman = {toml_str(s['roman'])}")
        out.append(f"title_es = {toml_str(s['title_es'])}")
        out.append(f"title_en = {toml_str(s['title_en'])}")
        # raw_html as a triple-string to preserve formatting verbatim
        out.append('raw_html = """')
        out.append(toml_escape(s['raw_html']))
        out.append('"""')
        out.append("")
    return "\n".join(out)


# Bibliography (Appendix C) -------------------------------------------------


def extract_bibliography(html: str) -> list[str]:
    """Extract every bibliography entry (one per <br><br> in the appendix paragraph)."""
    m = re.search(r'<h1>Full Bibliography</h1>\s*<p[^>]*>(.*?)</p>', html, re.DOTALL)
    if not m:
        return []
    raw = m.group(1)
    entries = [e.strip() for e in re.split(r"<br>\s*<br>\s*", raw) if e.strip()]
    return entries


def emit_bibliography(entries: list[str]) -> str:
    out = [
        "# Auto-extracted from legacy index.html (Appendix C). See scripts/extract.py.",
        "# Each entry preserves the original inline HTML (em, etc.) for byte-equivalent rendering.",
        "",
    ]
    for e in entries:
        out.append(f"[[entry]]")
        out.append(f"text = {toml_str(e)}")
        out.append("")
    return "\n".join(out)


# Section partials (HTML) --------------------------------------------------

SECTION_BOUNDARIES = [
    ("preface", "Preface", "Executive Summary"),
    ("executive-summary", "Executive Summary", "Context and Motivation"),
    ("01-context", "Context and Motivation", "The Contemporary Intellectual Context"),
    ("02-intellectual-context", "The Contemporary Intellectual Context", "The Founding Argument"),
    ("03-founding-argument", "The Founding Argument", "Program Identity and Positioning"),
    ("04-positioning", "Program Identity and Positioning", "Academic References and Inspiration"),
    ("05-references", "Academic References and Inspiration", "Pedagogical Model"),
    ("06-pedagogy", "Pedagogical Model", "Evaluation Framework"),
    ("07-evaluation", "Evaluation Framework", "Curriculum Overview"),
    ("08-curriculum", "Curriculum Overview", "Course Descriptions"),
    ("11-admissions", "Admissions", "Graduate Profile"),
    ("12-graduate-profile", "Graduate Profile", "References by Course and Institution"),
    ("appendix-a", "References by Course and Institution", "Evaluation Framework by Course"),
    ("appendix-b", "Evaluation Framework by Course", "Full Bibliography"),
]


def extract_section_partials(html: str) -> dict[str, str]:
    """Cut the legacy file into per-section HTML partials, preserving content."""
    parts: dict[str, str] = {}
    for slug, start_h1, end_h1 in SECTION_BOUNDARIES:
        s = html.find(f"<h1>{start_h1}</h1>")
        if s < 0:
            print(f"WARN: cannot find <h1>{start_h1}</h1>", file=sys.stderr)
            continue
        # Walk back to the preceding part-label or page-break for clean section start.
        section_start = html.rfind('<div class="page-break"', 0, s)
        if section_start < 0:
            section_start = s
        e = html.find(f"<h1>{end_h1}</h1>", s)
        if e < 0:
            section_end = len(html)
        else:
            # Walk back to the preceding page-break for clean section end.
            page_break_before_end = html.rfind('<div class="page-break"', 0, e)
            section_end = page_break_before_end if page_break_before_end > section_start else e
        parts[slug] = html[section_start:section_end].strip()
    return parts


def main() -> int:
    html = load()
    SECTIONS.mkdir(parents=True, exist_ok=True)

    courses = extract_courses(html)
    lookup_curriculum(html, courses)
    print(f"Extracted {len(courses)} courses.", file=sys.stderr)
    (DATA / "courses.toml").write_text(emit_courses(courses), encoding="utf-8")

    studios = extract_studios(html)
    print(f"Extracted {len(studios)} studios.", file=sys.stderr)
    (DATA / "studios.toml").write_text(emit_studios(studios), encoding="utf-8")

    bib = extract_bibliography(html)
    print(f"Extracted {len(bib)} bibliography entries.", file=sys.stderr)
    (DATA / "bibliography.toml").write_text(emit_bibliography(bib), encoding="utf-8")

    parts = extract_section_partials(html)
    for slug, h in parts.items():
        (SECTIONS / f"{slug}.html").write_text(h + "\n", encoding="utf-8")
    print(f"Wrote {len(parts)} section partials to {SECTIONS}", file=sys.stderr)

    print(f"All output under {DATA} and {SECTIONS}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
