#!/usr/bin/env python3
"""Verify exact Debian source versions and every .dsc source-file checksum."""
import argparse, hashlib, json, pathlib, re


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(manifest, directory):
    directory = pathlib.Path(directory)
    index = json.loads((directory / 'sources.json').read_text())
    required = {(r['source_package'], r['source_version'])
                for r in manifest['libraries'] + manifest.get('source_inputs', [])
                if 'source_package' in r}
    if not required <= {tuple(item) for item in index['packages']}:
        raise ValueError('Source index does not cover exact binary versions')
    for name, expected in index['files'].items():
        if pathlib.Path(name).name != name:
            raise ValueError('Invalid source index path')
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError('Source archive checksum mismatch: ' + name)
    described = set()
    for name in index['files']:
        if not name.endswith('.dsc'):
            continue
        text = (directory / name).read_text()
        source = re.search(r'^Source: (\S+)\s*$', text, re.M)
        version = re.search(r'^Version: (\S+)\s*$', text, re.M)
        checksums = re.search(r'^Checksums-Sha256:\n((?: [^\n]+\n)+)', text, re.M)
        if not source or not version or not checksums:
            raise ValueError('Incomplete source descriptor: ' + name)
        for line in checksums[1].splitlines():
            expected, size, filename = line.split()
            if filename not in index['files'] or index['files'][filename] != expected:
                raise ValueError('Descriptor/index mismatch: ' + filename)
            if (directory / filename).stat().st_size != int(size):
                raise ValueError('Source archive size mismatch: ' + filename)
        described.add((source[1], version[1]))
    if not required <= described:
        raise ValueError('Missing exact source descriptors: ' + repr(sorted(required - described)))
    return {'packages': len(required), 'files': len(index['files']),
            'bytes': sum((directory / name).stat().st_size for name in index['files'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=pathlib.Path)
    parser.add_argument('directory', type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.manifest.read_text()), args.directory)))
