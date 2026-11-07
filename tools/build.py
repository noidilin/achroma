"""Build a local, deterministic palette + Stylus release. Python stdlib only."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'applications/stylus'))
spec = importlib.util.spec_from_file_location('stylus_build', ROOT / 'applications/stylus/build.py')
stylus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stylus)
sys.path.insert(0, str(ROOT / 'tools'))
from contract import validate_mapping, validate_palette, validate_release


def write_json(path, data):
    stylus.atomic_write(path, stylus.json_bytes(data))


def build(output, cache, version, revision, *, fit_custom_colors=False):
    validate_release({'version': version, 'sourceRevision': revision})
    output, cache = Path(output).resolve(), Path(cache).resolve()
    # Producer artifacts must never overwrite source or installed application data.
    protected = [ROOT / name for name in
                 ('palette', 'applications', 'tools', 'tests', 'fixtures', 'schemas',
                  'licenses', 'docs', 'lib', '.git', '.github')]
    if output == ROOT or any(output == p or p in output.parents for p in protected):
        raise ValueError('Output must be outside source inputs')
    if cache == ROOT or any(cache == p or p in cache.parents for p in protected):
        raise ValueError('Cache must be outside source inputs')
    if output == cache or output in cache.parents or cache in output.parents:
        raise ValueError('Output and cache must be separate directories')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output directory must be absent or empty; use a fresh candidate')
    keys = stylus.load_json(ROOT / 'schemas/palette.schema.json')['required']
    palettes = {v: stylus.load_json(ROOT / f'palette/{v}.json') for v in ('dark', 'light')}
    for palette in palettes.values():
        validate_palette(palette, keys)
    mapping = stylus.load_json(ROOT / 'applications/stylus/mapping.json')
    validate_mapping(mapping)
    resolved = stylus.resolve_palettes(palettes, mapping)
    # The adapter is disposable generated data, not an independently edited palette.
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache, prefix='stage-') as temporary:
        stage = Path(temporary)
        config = stage / 'config'
        config.mkdir()
        write_json(config / 'palette.json', palettes)
        shutil.copyfile(ROOT / 'applications/stylus/mapping.json', config / 'mapping.json')
        if not fit_custom_colors:
            shutil.copyfile(ROOT / 'applications/stylus/filters.lock.json', config / 'filters.lock.json')
        shutil.copytree(ROOT / 'applications/stylus/vendor', config / 'vendor')
        native = stage / 'native'
        stylus.build(config, native, cache / 'stylus', fit_custom_colors=fit_custom_colors)
        report = stylus.load_json(native / 'build-report.json')
        if report['summary']['styles'] != 132:
            raise ValueError('Unexpected style count; review the contract before updating upstream')
        payload = stage / 'payload'
        for v in palettes:
            write_json(payload / f'palette/{v}.json', palettes[v])
        mappings = {}
        for variant, flavor in (('dark', 'mocha'), ('light', 'latte')):
            mappings[variant] = {
                'flavor': flavor, 'palette': resolved[variant],
                'usercssVariables': {'lightFlavor': 'latte', 'darkFlavor': 'mocha',
                                     'accentColor': mapping['accent']},
                'settings': {'updateInterval': 0},
            }
            write_json(payload / f'mappings/stylus/{variant}.json', mappings[variant])
            fragment = ''.join(f'@{key}: {color};\n' for key, color in resolved[variant].items())
            stylus.atomic_write(payload / f'fragments/stylus/{variant}.less', fragment.encode())
        for name in ('import.json', 'lib.less'):
            stylus.atomic_write(payload / 'themes/stylus' / name, (native / name).read_bytes())
        write_json(payload / 'reports/stylus-build.json', report)
        release = {'version': version, 'sourceRevision': revision}
        write_json(payload / 'data/consumer.json', {
            'schemaVersion': 1, 'release': release, 'palettes': palettes,
            'mappings': {'stylus': mappings},
        })
        shutil.copytree(ROOT / 'licenses', payload / 'licenses')
        sources = [ROOT / 'tools/build.py', ROOT / 'tools/contract.py', *sorted((ROOT / 'schemas').glob('*.json'))]
        sources += sorted((ROOT / 'palette').glob('*.json'))
        sources += sorted(p for p in (ROOT / 'applications/stylus').rglob('*') if p.is_file()
                          and '__pycache__' not in p.parts and p.suffix != '.pyc')
        sources += sorted(p for p in (ROOT / 'licenses').rglob('*') if p.is_file())
        manifest = {
            'schemaVersion': 1, 'release': release,
            'applications': {'stylus': {
                'format': 'Stylus UserCSS backup with Less sources',
                'compatibility': 'Stylus Less parens-division; browser import not automatically tested',
                'nativeNames': [s['name'] for s in stylus.load_json(native / 'import.json')
                                if 'sourceCode' in s],
                'styles': 132, 'flavors': {'dark': 'mocha', 'light': 'latte'},
            }},
            'buildInputs': {p.relative_to(ROOT).as_posix(): stylus.digest(p.read_bytes())
                            for p in sorted(sources)},
            'artifacts': {p.relative_to(payload).as_posix(): stylus.digest(p.read_bytes())
                          for p in sorted(payload.rglob('*')) if p.is_file()},
        }
        write_json(payload / 'manifest.json', manifest)
        archive_name = f'achroma-{version}.zip'
        archive_path = stage / archive_name
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_STORED) as archive:
            for p in sorted(payload.rglob('*')):
                if p.is_file():
                    info = zipfile.ZipInfo(p.relative_to(payload).as_posix(), (1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, p.read_bytes())
        checksum = f'{stylus.digest(archive_path.read_bytes())}  {archive_name}\n'
        output.mkdir(parents=True, exist_ok=True)
        shutil.copytree(payload, output / 'payload')
        shutil.copyfile(archive_path, output / archive_name)
        stylus.atomic_write(output / 'SHA256SUMS', checksum.encode())
    print(checksum, end='')


def deny_network(event, args):
    if event in ('socket.connect', 'socket.connect_ex', 'socket.getaddrinfo', 'socket.bind'):
        raise RuntimeError('Release generation is offline; network access denied')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--fit-custom-colors', action='store_true',
                        help='Explicitly bypass default lock for platform-dependent custom fitting')
    args = parser.parse_args()
    sys.addaudithook(deny_network)
    try:
        build(args.output, args.cache, args.version, args.source_revision,
              fit_custom_colors=args.fit_custom_colors)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'achroma: {error}\n')


if __name__ == '__main__':
    main()
