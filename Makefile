.DEFAULT_GOAL := help
SHELL := /bin/bash
export DEST

.PHONY: help build renderer extension check check-renderer check-gnome check-maintenance check-integration check-overview stage-manager stage-ui package inventory clean-tests clean-tests-apply

help:
	@printf '%s\n' 'build / renderer / extension: build only; no installation' 'check: renderer, GNOME and cleanup safety checks' 'check-integration / check-overview: isolated graphical tests' 'stage-manager / stage-ui: prepare isolated test sessions' 'package DEST=/new/path: create an independent runtime' 'inventory: directory sizes and Git status' 'clean-tests: preview disposable test directories' 'clean-tests-apply: remove stopped test directories after safety checks'

build: renderer extension
renderer:
	bash renderer/scripts/build.sh
extension:
	bash gnome/scripts/build.sh
check: check-renderer check-gnome check-maintenance
check-renderer:
	bash renderer/tests/check.sh
check-gnome:
	bash gnome/tests/check.sh
check-maintenance:
	python3 -B integration/tests/check-maintenance.py
check-integration:
	bash integration/tests/check.sh --integration
check-overview:
	python3 integration/tests/check-static-overview.py
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
