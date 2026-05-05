# Licenciatura en Sistemas Complejos

Proposal document for a new undergraduate degree at the Universidad de Buenos Aires.

**Live (legacy single-file build):** <https://unbalancedparentheses.github.io/licenciatura-en-sistemas-complejos/>
**Status:** Draft / Not yet approved

---

## Migration in progress

The document is being migrated from a single hand-edited `index.html` to a [Zola](https://www.getzola.org/) static site so that:

- Course data lives in TOML (single source of truth — no more "40 vs 39 courses" mismatches).
- Narrative sections are Markdown (reviewable diffs).
- Audience filtering (Students / Faculty / Authorities) is declarative via front matter.
- Stats are generated from data, not typed.

Until the generated build matches the legacy `index.html`, both coexist:

- `index.html` (root) — current published version.
- `site/` — Zola project, work in progress.

## Develop

Requires [Nix](https://nixos.org/) (with flakes enabled) for reproducible deps.

```sh
nix develop          # enter dev shell with zola, make, taplo
make dev             # zola serve --open at localhost:1111
make build           # build static site to site/public
make clean           # remove build artifacts
make help            # list targets
```

## Layout

```
flake.nix            Nix dev shell (zola, make, taplo)
Makefile             Conventional commands
index.html           Legacy single-file build (still deployed)
site/
  config.toml        Zola config + program metadata
  data/
    program.toml     Years, blocks, cohort size, status
    audiences.toml   Audience labels
    courses.toml     All course descriptions
    curriculum.toml  Year/block grid + studios
  content/           Narrative sections in Markdown
  templates/         Tera templates
    index.html       Base layout
    macros/
      course.html    Course card macro
  static/            Plain assets (CSS, JS)
```

## Contributing

- **Add or change a course** → edit `site/data/courses.toml`.
- **Edit narrative prose** → edit the matching `site/content/*.md`.
- **Change a stat** → edit `site/data/program.toml` (counts derived where possible).
- **Add an audience-filtered section** → set `audiences = [...]` in front matter.
