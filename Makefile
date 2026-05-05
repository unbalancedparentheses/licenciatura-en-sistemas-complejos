.PHONY: dev build clean check serve pdf extract help

SITE_DIR := site

help:
	@echo "lsc · program proposal site"
	@echo ""
	@echo "Targets:"
	@echo "  make dev      Start Zola dev server with live reload"
	@echo "  make build    Build static site to $(SITE_DIR)/public"
	@echo "  make pdf      Build site then export 8 PDFs (audience × language)"
	@echo "  make check    Validate Zola config + content"
	@echo "  make clean    Remove build artifacts"
	@echo "  make serve    Build then preview at localhost:1111"
	@echo "  make extract  Re-run scripts/extract.py from legacy index.html"
	@echo ""
	@echo "Use 'nix develop' to enter the dev shell with all deps."

dev:
	cd $(SITE_DIR) && zola serve --open

build:
	cd $(SITE_DIR) && zola build

pdf: build
	python3 scripts/build_pdfs.py

extract:
	python3 scripts/extract.py

check:
	cd $(SITE_DIR) && zola check

clean:
	rm -rf $(SITE_DIR)/public

serve: build
	cd $(SITE_DIR)/public && python3 -m http.server 1111
