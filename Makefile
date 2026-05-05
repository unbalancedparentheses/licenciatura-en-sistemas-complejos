.PHONY: dev build clean check serve deploy help

SITE_DIR := site

help:
	@echo "lsc · program proposal site"
	@echo ""
	@echo "Targets:"
	@echo "  make dev      Start Zola dev server with live reload"
	@echo "  make build    Build static site to $(SITE_DIR)/public"
	@echo "  make check    Validate Zola config + content"
	@echo "  make clean    Remove build artifacts"
	@echo "  make serve    Build then preview at localhost:1111"
	@echo ""
	@echo "Use 'nix develop' to enter the dev shell with all deps."

dev:
	cd $(SITE_DIR) && zola serve --open

build:
	cd $(SITE_DIR) && zola build

check:
	cd $(SITE_DIR) && zola check

clean:
	rm -rf $(SITE_DIR)/public

serve: build
	cd $(SITE_DIR)/public && python3 -m http.server 1111
