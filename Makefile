.DEFAULT_GOAL := help
SHELL := /bin/bash
export DEST
export WALLPAPER_BUILD_DIR

.PHONY: install extension-dev package-backend check-packaging release-package help build renderer extension check check-renderer check-gnome check-maintenance check-licenses check-integration check-overview check-runtime-capture stage-manager stage-ui package inventory clean-tests clean-tests-apply

release-package:
	python3 integration/scripts/package-release.py

help:
	@printf '%s\n' 'build / renderer / extension: build only; no installation' 'install: package an existing backend build and explicitly install the full extension' 'release-package: full release assets and sources in dist/VERSION (must not exist)' 'check: renderer, GNOME, license notices and cleanup safety checks' 'check-integration / check-overview: isolated graphical tests' 'stage-manager / stage-ui: prepare isolated test sessions' 'package DEST=/new/path: create an independent runtime' 'inventory: directory sizes and Git status' 'clean-tests: preview disposable test directories' 'clean-tests-apply: remove stopped test directories after safety checks'

build: package-backend
	$(MAKE) extension
renderer:
	bash renderer/scripts/build.sh
extension-dev:
	bash gnome/scripts/build.sh
extension:
	python3 packaging/build-package.py --build-dir "$${WALLPAPER_BUILD_DIR:-$(CURDIR)/build/package-renderer}" --output "$${DEST:-$(CURDIR)/dist/development}"
check: check-renderer check-gnome check-maintenance check-licenses check-packaging
check-renderer:
	bash renderer/tests/check.sh
check-gnome:
	bash gnome/tests/check.sh
check-licenses:
	python3 -B integration/tests/check-runtime-notices.py
check-maintenance:
	python3 -B integration/tests/check-maintenance.py
check-integration:
	bash integration/tests/check.sh --integration
check-overview:
	python3 integration/tests/check-static-overview.py
check-runtime-capture:
	python3 integration/tests/check-runtime-capture.py
stage-manager:
	python3 integration/tests/stage-manager-test.py
stage-ui:
	python3 integration/tests/stage-manager-ui-test.py
package:
	@test -n "$$DEST" || { echo 'Set DEST to a new runtime directory.' >&2; exit 1; }
	python3 integration/scripts/package-runtime.py "$$DEST"
inventory:
	python3 -B integration/scripts/maintenance.py inventory
clean-tests:
	python3 -B integration/scripts/maintenance.py clean-tests
clean-tests-apply:
	python3 -B integration/scripts/maintenance.py clean-tests --apply

check-packaging:
	python3 packaging/test-data.py
	python3 packaging/test-install.py
	python3 packaging/test-sources.py
	python3 packaging/test-source-snapshot.py

package-backend:
	bash packaging/build-backend.sh

install:
	python3 packaging/install-from-build.py --build-dir "$${WALLPAPER_BUILD_DIR:-$(CURDIR)/build/package-renderer}"
