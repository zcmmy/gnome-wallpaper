"""Collect notices for the existing local runtime layout; do not package resources."""
import json
import re
import shutil
from pathlib import Path

PRIVATE_LIBRARY_PACKAGES = {
    'libGLEW.so.2.2': 'libglew2.2', 'libmpv.so.2': 'libmpv2',
    'libglfw.so.3': 'libglfw3', 'libmujs.so.3': 'libmujs3',
    'libavdevice.so.61': 'libavdevice61', 'liblua5.2.so.0': 'liblua5.2-0',
    'libjack.so.0': 'libjack0', 'libsndio.so.7': 'libsndio7.0',
    'libsixel.so.1': 'libsixel1', 'libXpresent.so.1': 'libxpresent1',
    'libva-wayland.so.2': 'libva-wayland2', 'libexpat.so.1': 'libexpat1',
}
COMMON_LICENSES = ('GPL-2', 'LGPL-2', 'LGPL-2.1', 'LGPL-3', 'Apache-2.0')


def collect_notices(root, sysroot, build_output, destination, private_libraries,
                    common_licenses=Path('/usr/share/common-licenses')):
    """Fail closed on missing/unknown notices; source delivery is a separate duty."""
    unknown = set(private_libraries) - PRIVATE_LIBRARY_PACKAGES.keys() - {
        'liblinux-wallpaperengine-lib.so'}
    if unknown:
        raise ValueError('Missing license mapping for private libraries: ' + ', '.join(sorted(unknown)))
    index = json.loads((root / 'third_party/licenses.json').read_text())
    names = index['bundled_external_license_files'] + index['additional_license_files']
    names += ['LICENSE', 'NOTICE.md', 'renderer/source/LICENSE',
              'third_party/licenses.json', 'third_party/sources.lock.json',
              'third_party/README.md', 'third_party/COMPONENT-NOTICES.md',
              'renderer/source/CMakeModules/README.md']
    copies = []
    for name in sorted(set(names)):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe license index path: ' + name)
        copies.append((root / relative, destination / 'source' / relative))
    packages = {PRIVATE_LIBRARY_PACKAGES[name] for name in private_libraries
                if name in PRIVATE_LIBRARY_PACKAGES}
    # These headers/protocol definitions contribute code despite not appearing in ldd.
    packages.add('libglm-dev')
    protocols = sorted((build_output.parent / 'wayland').glob('*-protocol.c'))
    if protocols:
        packages.add('wayland-protocols')
    for package in sorted(packages):
        copies.append((sysroot / 'share/doc' / package / 'copyright',
                       destination / (package + '-copyright')))
    common_names = set(COMMON_LICENSES)
    for source, _ in copies:
        if not source.is_file():
            raise FileNotFoundError('Required license notice not found: ' + str(source))
        common_names.update(re.findall(r'/usr/share/common-licenses/([\w.+-]+)', source.read_text()))
    for name in sorted(common_names):
        copies.append((common_licenses / name, destination / 'common' / name))
    # Preflight before writing: a changed build must not silently omit a notice.
    for source, _ in copies:
        if not source.is_file():
            raise FileNotFoundError('Required license notice not found: ' + str(source))
    protocol_notices = []
    for source in protocols:
        text = source.read_text()
        # wayland-scanner writes the protocol copyright as the second block comment.
        blocks = text.split('/*')
        notices = [block.split('*/', 1)[0].strip() for block in blocks[1:]
                   if '*/' in block and 'Copyright' in block.split('*/', 1)[0]]
        if not notices:
            raise ValueError('Generated protocol lacks a copyright notice: ' + str(source))
        protocol_notices.append((source.name + '.LICENSE', '\n\n'.join(notices) + '\n'))
    for source, target in copies:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for name, text in protocol_notices:
        target = destination / 'protocols' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    (destination / 'README.md').write_text("""# Runtime license notices

`source/` preserves the source notice index and attribution paths. It deliberately
includes build/test-only notices as well as compiled components; it is not a list
of libraries loaded at runtime. Original source-document links may refer to files
available only in the source repository.

Package `*-copyright` files come from the sysroot actually used for this package.
`protocols/` contains copyright blocks from its generated Wayland C files.
`common/` supplies the license texts referenced by Debian copyright notices.
The runtime manifest records copied libraries and hashes of all packaged files.

These notices do not replace GPL/LGPL corresponding-source obligations. A public
binary release still needs the applicable complete source and build materials.
Wallpaper Engine assets and user wallpapers are not licensed by these notices.
""")
