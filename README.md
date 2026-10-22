# Licenciatura en Sistemas Complejos

Proposal document for a new undergraduate degree at the Universidad de Buenos Aires.

- **Live site:** <https://unbalancedparentheses.github.io/licenciatura-en-sistemas-complejos/>
- **Status:** Draft

The site is built with [Zola](https://www.getzola.org/) from data files (`site/data/*.toml`) and HTML/Tera partials (`site/templates/`). Every push to `main` triggers a GitHub Actions deploy that rebuilds the site, regenerates 8 PDFs (4 audiences × 2 languages) via headless Chrome, and publishes to GitHub Pages.

## Audiences and PDFs

The same source produces four URLs and eight PDFs:

| URL | PDF (ES) | PDF (EN) |
|---|---|---|
| `/`              | `pdf/full-es.pdf`        | `pdf/full-en.pdf` |
| `/students/`     | `pdf/students-es.pdf`    | `pdf/students-en.pdf` |
| `/faculty/`      | `pdf/faculty-es.pdf`     | `pdf/faculty-en.pdf` |
| `/authorities/`  | `pdf/authorities-es.pdf` | `pdf/authorities-en.pdf` |

The audience pages share the same prose; they differ in which sections are rendered (e.g., `/students/` drops the academic-references appendices and §9 course descriptions).

A language switcher (top-right) toggles between Spanish (default) and English in real time. Each prose paragraph is bilingual: `<p lang="es">` and `<p lang="en">` siblings filtered by `body[data-lang]`.

## Develop

Requires [Nix](https://nixos.org/) with flakes enabled.

```sh
nix develop                           # enter dev shell (zola, make, python3, pandoc)
make dev                              # zola serve --open at localhost:1111
make build                            # build static site to site/public
make pdf                              # build + export 8 PDFs to site/public/pdf
make validate                         # data, bibliography, link checks
make clean                            # remove build artifacts
make help                             # list all targets
```

PDF export needs a Chromium-class browser. CI uses `browser-actions/setup-chrome`; locally the dev shell installs `chromium` on Linux. **macOS users:** chromium is not built for `aarch64-darwin` in nixpkgs, so use the system Chrome:

```sh
LSC_BROWSER="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" make pdf
```

## Layout

```
flake.nix            Nix dev shell
Makefile             Conventional commands (dev, build, pdf, validate, ...)
.github/workflows/
  deploy.yml         Builds site + PDFs, deploys to GitHub Pages on push to main
scripts/
  extract.py         One-shot extraction from the legacy index.html (no longer needed for steady-state work)
  build_pdfs.py      Runs headless Chrome against each audience+language URL
  validate.py        Data/link/PDF validators; also checks that course/taller counts and total hours match program.toml
site/
  config.toml        Zola config + program-level metadata
  data/
    program.toml     Years, cuatrimestres, weeks per bimestre, Curso Introductorio hours,
                     expected counts and total hours, cohort size, status
    audiences.toml   Audience labels (ES/EN)
    courses.toml     31 courses: cuatrimestre, position, weekly hours per bimestre
                     (`hours = [B1, B2]`), núcleo, descriptions, references, evaluations
    talleres.toml    8 Talleres Integradores: cuatrimestre, weekly hours per bimestre,
                     §10 description fields, references, evaluations
    curriculum.toml  Stages, núcleos and year grouping used to present the plan
    bibliography.toml  Appendix C entries with canonical URLs
  content/           Section index pages (front-matter-only stubs)
  templates/
    index.html       Full document (all sections)
    audience.html    Per-audience views (filters which sections render)
    partials/        Plan views generated from data: stages, hours tables, load chart, stats
    macros/
      course.html    Course-card macro
      taller.html    Taller-card macro (§10)
      layout.html    Cover, top-nav, footer macros (shared by both top-level templates)
    sections/        15 narrative-section partials (bilingual HTML/Tera; appendices A and B are generated from courses.toml and talleres.toml)
  sass/              SCSS partials, compiled to public/style.css by Zola
  static/            JS, additional static assets
```

## Contributing

- **Add or change a course** → edit `site/data/courses.toml`. `cuatrimestre` and `position` determine where it appears in the plan tables; `hours = [B1, B2]` gives its weekly contact hours in each of the two 8-week bimestres of the cuatrimestre (0 if it does not run in that bimestre). The hours tables, load chart, totals, §9 details and appendices A and B are all rendered from the same entry.
- **Add or change a Taller Integrador** → edit `site/data/talleres.toml`. `cuatrimestre` and `hours` place it in the plan; the remaining fields are the §10 description.
- **Change a program-level stat** (years, cohort size, Curso Introductorio hours) → edit `site/data/program.toml`. Counts and total hours are computed from the course and taller data; `validate.py` also checks that course/taller counts and total hours match `program.toml`.
- **Edit narrative prose** → edit the matching `site/templates/sections/NN-*.html`. Each prose element has bilingual ES/EN siblings, keep both in sync.
- **Add a bibliography entry** → append to `site/data/bibliography.toml`. Every entry should have a canonical `url` (publisher page, DOI, arXiv, or open-access copy).
- **Run before pushing**: `make build && make validate` (without `--skip-pdf-links` if Chrome is available).
