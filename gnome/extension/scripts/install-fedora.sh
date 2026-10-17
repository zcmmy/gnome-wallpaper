#!/bin/bash
# The old combined installer is retained in Git history and the migration backup.
echo 'The combined Fedora/renderer installer was retired in this workspace.' >&2
echo 'Build only this extension: scripts/package.sh /absolute/path/extension.zip' >&2
echo 'Install dependencies and the renderer separately; packaging never enables autostart.' >&2
exit 2
