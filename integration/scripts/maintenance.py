#!/usr/bin/env python3
"""Inventory and explicit, guarded cleanup of disposable development profiles."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DISPOSABLE = (
    'runtime/capture-test', 'runtime/manager-hot-test', 'runtime/manager-test',
    'runtime/manager-ui-test', 'runtime/static-background-test',
    'runtime/static-overview-test', 'runtime/runtime-capture-test', 'runtime/nested',
    'gnome/extension/__pycache__', 'gnome/scripts/__pycache__',
    'integration/tests/__pycache__', 'integration/scripts/__pycache__',
)


def byte_size(path):
    if path.is_symlink():
        return path.lstat().st_size
    if path.is_file():
        return path.stat().st_size
    total = 0
    for parent, dirs, files in os.walk(path, followlinks=False):
        for name in files:
            total += (Path(parent) / name).lstat().st_size
        dirs[:] = [name for name in dirs if not (Path(parent) / name).is_symlink()]
    return total


def mounted_paths():
    # mountinfo encodes spaces, tabs, newlines and backslashes as octal escapes.
    import re
    return [Path(re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), line.split()[4]))
            for line in Path('/proc/self/mountinfo').read_text().splitlines()]


def validate_path(root, relative):
    if relative not in DISPOSABLE:
        raise RuntimeError(f'Not in cleanup whitelist: {relative}')
    target = root / relative
    for part in [target, *target.parents]:
        if part.is_symlink():
            raise RuntimeError(f'Symlink in cleanup path: {part}')
        if part == root:
            break
    if not target.exists():
        return target
    if not target.is_dir():
        raise RuntimeError(f'Not a directory: {target}')
    if any(mount == target or target in mount.parents for mount in mounted_paths()):
        raise RuntimeError(f'Mounted filesystem inside cleanup path: {target}')
    return target


def process_references(paths):
    """Inspect own-user processes; never expose environment contents in reports."""
    references, errors = [], []
    needles = {str(path): os.fsencode(path) for path in paths}
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            command = (process / 'cmdline').read_bytes()
            if not command:  # zombie or kernel thread cannot retain a test session
                continue
            # Login infrastructure is not a wallpaper test session. These fixed
            # commands are commonly non-dumpable even to the session owner.
            if command in (b'/usr/lib/systemd/systemd\0--user\0',
                           b'(sd-pam)\0', b'/usr/bin/ssh-agent\0-D\0'):
                continue
            environment = (process / 'environ').read_bytes()
            cwd = os.fsencode(os.readlink(process / 'cwd'))
            blob = command + b'\0' + environment + b'\0' + cwd
            for path, needle in needles.items():
                if needle in blob:
                    references.append({'pid': int(process.name), 'path': path})
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (PermissionError, OSError) as exc:
            errors.append({'pid': int(process.name), 'error': type(exc).__name__})
    return references, errors


def clean(root, apply=False):
    candidates = [validate_path(root, relative) for relative in DISPOSABLE]
    candidates = [path for path in candidates if path.exists()]
    references, errors = process_references(candidates)
    result = {'time': datetime.datetime.now().astimezone().isoformat(), 'applied': apply,
              'candidates': [{'path': str(p.relative_to(root)), 'bytes': byte_size(p)} for p in candidates],
              'references': references, 'inspection_errors': errors, 'removed': [], 'removed_bytes': 0}
    if apply:
        if references or errors:
            raise RuntimeError('Cleanup refused; active references or inaccessible processes: ' +
                               json.dumps({'references': references, 'inspection_errors': errors}))
        for entry in result['candidates']:
            target = validate_path(root, entry['path'])
            # Recheck immediately before each removal, including newly started processes.
            references, errors = process_references([target])
            if references or errors:
                raise RuntimeError(f'Cleanup interrupted before {target}: {references}, {errors}')
            shutil.rmtree(target)
            result['removed'].append(entry['path'])
            result['removed_bytes'] += entry['bytes']
            save_report(root, result)
    return result


def save_report(root, result):
    directory = root / 'reports/maintenance'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('cleanup-' + result['time'].replace(':', '-') + '.json')
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def inventory(root):
    directories = {p.name: byte_size(p) for p in sorted(root.iterdir()) if p.is_dir() and not p.is_symlink()}
    result = subprocess.run(['git', '-C', str(root), 'status', '--short'],
                            capture_output=True, text=True, check=True)
    return {'root': str(root), 'directory_bytes': directories,
            'repository_status': result.stdout.splitlines(),
            'upstreams': json.loads((root / 'third_party/sources.lock.json').read_text()),
            'cleanup': clean(root)}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inventory', 'clean-tests'])
    parser.add_argument('--apply', action='store_true', help='Remove only guarded, whitelisted test directories')
    args = parser.parse_args()
    if args.apply and args.command != 'clean-tests':
        parser.error('--apply is only valid for clean-tests')
    try:
        result = inventory(ROOT) if args.command == 'inventory' else clean(ROOT, args.apply)
    except RuntimeError as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
