# Local development guidance

This directory is part of the top-level gnome-wallpaper Git repository.
Read ../../README.md, ../../docs/DEVELOPMENT.md and ../README.md for the current integration.
Upstream docs in this directory describe the original extension and may be historical.

- Keep renderer implementation separate from GNOME Shell, GTK and deployment code.
- Use ../scripts/build.sh to package; use ../tests/check.sh for regression checks.
- Install via ../scripts/install-extension.py, which stages schemas and atomically swaps directories.
- Never truncate or recompile gschemas.compiled in a live installed extension directory.
- Do not restart GNOME, change desktop appearance or enable startup as a side effect of development.
- Prefer an isolated test Shell; normal Shell modules remain cached for the current session.
- Keep asynchronous teardown, cancellation and process ownership checks intact.
- Do not add Co-Authored-By trailers.
