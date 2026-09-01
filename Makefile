.PHONY: release

# Create and push an annotated tag to trigger the release workflow.
# Usage: make release VERSION=v2026.7.0 MESSAGE="description of release"
release:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make release VERSION=v2026.7.0 MESSAGE=\"...\""; exit 1; fi
	@if [ -z "$(MESSAGE)" ]; then echo "MESSAGE is required"; exit 1; fi
	@if ! echo "$(VERSION)" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9._-]+)?$$'; then echo "Invalid semver: $(VERSION)"; exit 1; fi
	@if [ -n "$$(git status --porcelain)" ]; then echo "Working tree dirty — commit or stash first"; exit 1; fi
	@if [ "$$(git branch --show-current)" != "main" ]; then echo "Not on main branch"; exit 1; fi
	git tag -a $(VERSION) -m "$(MESSAGE)"
	git push origin $(VERSION)
	@echo ""
	@echo "Tagged and pushed $(VERSION) — watch: gh run watch"
