"""Offline Achroma UserCSS builder; run `python build.py --help`."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.request

sys.dont_write_bytecode = True
import filters

HERE = Path(__file__).resolve().parent
ROLES = ('rosewater flamingo pink mauve red maroon peach yellow green teal sky '
         'sapphire blue lavender text subtext1 subtext0 overlay2 overlay1 overlay0 '
         'surface2 surface1 surface0 base mantle crust').split()
IMPORT = re.compile(r'@import\s+(?:\([^)]*\)\s*)?(?:url\(\s*)?'
                    r'[\"\']([^\"\']+)[\"\']\s*\)?\s*([^;]*);')
CSS_URLS = {
    'pygments.css': 'https://python.catppuccin.com/pygments/catppuccin-variables.important.css',
    'prism.css': 'https://prismjs.catppuccin.com/variables.important.css',
    'highlightjs.css': 'https://unpkg.com/@catppuccin/highlightjs@1.0.0/css/catppuccin-variables.css',
    'highlightjs-important.css': 'https://unpkg.com/@catppuccin/highlightjs@1.0.0/css/catppuccin-variables.important.css',
}
EXCLUDED = {
    'Codeberg Catppuccin': 'Imports precompiled Gitea themes with hardcoded colors.',
    'PythonAnywhere Catppuccin': 'Imports precompiled Chroma themes with hardcoded colors.',
}
STANDARD_URLS = {
    'https://userstyles.catppuccin.com/lib/lib.less',
    'https://userstyles.catppuccin.com/lib/std/v1.less',
    'https://noidilin.github.io/achroma/lib/lib.less',
}
HEX = re.compile(r'#[0-9a-fA-F]{6}\Z')
UPDATE_META = re.compile(r'^\s*@updateURL\b[^\n]*\n?', re.M | re.I)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def resolve_palettes(palettes, mapping):
    result = {}
    for variant in ('light', 'dark'):
        source = palettes[variant]
        result[variant] = {}
        for role in ROLES:
            key = mapping.get('roles', {}).get(role, role)
            color = source.get(key)
            if not isinstance(color, str) or not HEX.fullmatch(color):
                raise ValueError(f'{variant}.{role}: invalid or missing palette key {key!r}')
            result[variant][role] = color.lower()
    unknown = set(mapping.get('roles', {})) - set(ROLES)
    if unknown:
        raise ValueError(f'Unknown browser roles: {sorted(unknown)}')
    return result


def replace_flavor(source, variable, flavor, replacement):
    # Restrict edits to the known detached-map layout. API drift must fail loudly.
    pattern = re.compile(r'(@' + re.escape(variable) + r':\s*\{.*?)(@' + flavor
                         + r':\s*\{)[^{}]*(\};)', re.S)
    source, count = pattern.subn(lambda m: m[1] + m[2] + ' ' + replacement + ' ' + m[3], source)
    if count != 1:
        raise ValueError(f'Expected one @{variable}.@{flavor} map, found {count}')
    return source


def make_library(standard, palettes, filter_values):
    for variant, flavor in (('light', 'latte'), ('dark', 'mocha')):
        colors = ' '.join(f'@{role}: {value};' for role, value in palettes[variant].items())
        icons = ' '.join(f'@{role}: {filter_values[value]["css"]};'
                         for role, value in palettes[variant].items())
        standard = replace_flavor(standard, 'catppuccin', flavor, colors)
        standard = replace_flavor(standard, 'catppuccin-filters', flavor, icons)
    if IMPORT.search(standard):
        raise ValueError('Standard library unexpectedly contains imports')
    return '/* Achroma generated palette; Catppuccin standard library, MIT. */\n' + standard


def choose_var(variables, name, value):
    if name not in variables:
        return
    variable = variables[name]
    if variable.get('type') != 'select' or value not in {
        option['name'] for option in variable.get('options', [])
    }:
        raise ValueError(f'{name} does not support {value!r}')
    variable['value'] = value


def transform(records, library, accent, dependencies=None):
    records = copy.deepcopy(records)
    dependencies = dependencies or {}
    count = 0
    for style in records:
        if 'settings' in style:
            style['settings']['updateInterval'] = 0
        if 'sourceCode' not in style:
            if 'settings' not in style:
                raise ValueError('Unexpected non-UserCSS record')
            continue
        count += 1
        name = style.get('name', f'style {count}')
        metadata = style.get('usercssData', {})
        if metadata.get('preprocessor') != 'less':
            raise ValueError(f'{name}: only Less UserCSS is supported')
        source = style['sourceCode']
        urls = [m[1] for m in IMPORT.finditer(source)]
        if sum(url in STANDARD_URLS for url in urls) != 1:
            raise ValueError(f'{name}: expected exactly one supported standard-library import: {urls}')

        def inline(match):
            url, media = match.groups()
            if url in STANDARD_URLS and not media:
                return library
            if url in dependencies and not media:
                return dependencies[url]
            raise ValueError(f'{name}: unsupported dependency: {url} {media}')

        source = IMPORT.sub(inline, source)
        source = UPDATE_META.sub('', source)
        # Belt and braces: fail on unfamiliar imports, including unquoted syntax.
        if re.search(r'@import\b', source):
            raise ValueError(f'{name}: unresolved import')
        variables = metadata.get('vars', {})
        for key, value in (('lightFlavor', 'latte'), ('darkFlavor', 'mocha'), ('accentColor', accent)):
            choose_var(variables, key, value)
        for key in ('updateUrl', 'updateURL', 'originalDigest', 'sections'):
            style.pop(key, None)
        for key in ('updateUrl', 'updateURL'):
            metadata.pop(key, None)
        style['sourceCode'] = source
    if not count:
        raise ValueError('No UserCSS styles found')
    return records


def inspect(records):
    summary = {'styles': 0, 'settings_records': 0, 'imports': [], 'update_urls': [],
               'light_flavors': [], 'dark_flavors': [], 'accents': []}
    for style in records:
        if 'settings' in style:
            summary['settings_records'] += 1
        if 'sourceCode' not in style:
            continue
        summary['styles'] += 1
        summary['imports'].extend(m[1] for m in IMPORT.finditer(style['sourceCode']))
        metadata = style.get('usercssData', {})
        for obj in (style, metadata):
            summary['update_urls'].extend(obj[k] for k in ('updateUrl', 'updateURL') if obj.get(k))
        if UPDATE_META.search(style['sourceCode']):
            summary['update_urls'].append('sourceCode @updateURL')
        for variable, field in (('lightFlavor', 'light_flavors'), ('darkFlavor', 'dark_flavors'),
                                ('accentColor', 'accents')):
            value = metadata.get('vars', {}).get(variable)
            if value:
                summary[field].append(value.get('value') or value.get('default'))
    for key in ('imports', 'update_urls', 'light_flavors', 'dark_flavors', 'accents'):
        summary[key] = sorted(set(summary[key]))
    return summary


def vendor_inputs(directory):
    lock = load_json(directory / 'upstream.lock.json')
    if lock.get('schema') != 1:
        raise ValueError('Unsupported upstream lock schema')
    inputs = {}
    required = {'export.json', 'std.less', 'LICENSE', *CSS_URLS}
    if set(lock['files']) != required:
        raise ValueError('Unexpected vendor file set')
    for name in sorted(required):
        data = (directory / name).read_bytes()
        if digest(data) != lock['files'][name]['sha256']:
            raise ValueError(f'Checksum mismatch: {name}')
        inputs[name] = data
    return lock, inputs


def build(config, destination, cache):
    mapping = load_json(config / 'mapping.json')
    palettes = resolve_palettes(load_json(config / 'palette.json'), mapping)
    lock, inputs = vendor_inputs(config / 'vendor')
    fingerprint = digest(b''.join([
        (config / 'palette.json').read_bytes(), (config / 'mapping.json').read_bytes(),
        json_bytes(lock), Path(__file__).read_bytes(), (HERE / 'filters.py').read_bytes(),
    ]))
    report_path = destination / 'build-report.json'
    export_path = destination / 'import.json'
    if report_path.exists() and all((destination / name).exists() for name in ('import.json', 'lib.less')):
        previous = load_json(report_path)
        if previous.get('fingerprint') == fingerprint and all(
            digest((destination / name).read_bytes()) == checksum
            for name, checksum in previous.get('artifacts', {}).items()
        ) and set(previous.get('artifacts', {})) == {'import.json', 'lib.less'}:
            print(f'Unchanged: {export_path}')
            return
    cache_path = cache / f'filters-v{filters.VERSION}.json'
    # Fitting these muted colors is cheap. Recompute deterministically rather than
    # allowing a stale/corrupt cache to influence a release artifact.
    fitted = {color: filters.fit(color) for color in sorted(
        {c for palette in palettes.values() for c in palette.values()}
    )}
    library = ('/*\n' + inputs['LICENSE'].decode().replace('*/', '* /') + '*/\n'
               + make_library(inputs['std.less'].decode(), palettes, fitted))
    upstream_records = json.loads(inputs['export.json'])
    excluded = {s['name']: EXCLUDED[s['name']] for s in upstream_records if s.get('name') in EXCLUDED}
    dependencies = {url: inputs[name].decode() for name, url in CSS_URLS.items()}
    records = transform([s for s in upstream_records if s.get('name') not in EXCLUDED],
                        library, mapping.get('accent', 'rosewater'), dependencies)
    summary = inspect(records)
    if summary['imports'] or summary['update_urls']:
        raise ValueError(f'Unsafe output: {summary}')
    export = json_bytes(records)
    report = {'schema': 1, 'fingerprint': fingerprint, 'upstream': lock,
              'summary': summary, 'excluded_styles': excluded, 'palettes': palettes, 'filters': fitted,
              'artifacts': {'import.json': digest(export), 'lib.less': digest(library.encode())},
              'validation': 'Structural checks only; run the repository compiler checks before import.'}
    # Every transformation succeeds before touching previously generated artifacts.
    atomic_write(cache_path, json_bytes(fitted))
    atomic_write(destination / 'lib.less', library.encode())
    atomic_write(export_path, export)
    atomic_write(report_path, json_bytes(report))
    print(f'Built {summary["styles"]} styles: {export_path}')
    for name, reason in excluded.items():
        print(f'Excluded {name}: {reason}')


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'achroma-stylus-builder'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def update(directory, commit, export_url):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ValueError('--commit must be a full Catppuccin userstyles commit SHA')
    base = f'https://raw.githubusercontent.com/catppuccin/userstyles/{commit}'
    urls = {'export.json': export_url, 'std.less': f'{base}/lib/std/v1.less',
            'LICENSE': f'{base}/LICENSE', **CSS_URLS}
    inputs = {name: download(url) for name, url in urls.items()}
    # Validate the snapshot's dependency layout before writing anything.
    transform([s for s in json.loads(inputs['export.json']) if s.get('name') not in EXCLUDED],
              inputs['std.less'].decode(), 'rosewater',
              {url: inputs[name].decode() for name, url in CSS_URLS.items()})
    lock = {'schema': 1, 'standard_commit': commit,
            'note': 'Export release is independently pinned by checksum; compile-check before promotion.',
            'files': {name: {'url': urls[name], 'sha256': digest(data)} for name, data in inputs.items()}}
    for name, data in inputs.items():
        atomic_write(directory / name, data)
    atomic_write(directory / 'upstream.lock.json', json_bytes(lock))
    print(f'Updated pinned inputs: {directory}. Rebuild and run compiler checks before importing.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build_parser = commands.add_parser('build', help='Offline build from explicitly staged, locked inputs')
    build_parser.add_argument('--config', type=Path, required=True)
    build_parser.add_argument('--output', type=Path, required=True)
    build_parser.add_argument('--cache', type=Path, required=True)
    check = commands.add_parser('check', help='Verify generated artifact hashes and safety (not compilation)')
    check.add_argument('--output', type=Path, required=True)
    examine = commands.add_parser('examine', help='Inspect a generated or legacy Stylus export')
    examine.add_argument('file', type=Path)
    refresh = commands.add_parser('update', help='Explicit network refresh of repository vendor inputs')
    refresh.add_argument('--vendor-dir', type=Path, required=True)
    refresh.add_argument('--commit', required=True)
    refresh.add_argument('--export-url', default='https://github.com/catppuccin/userstyles/releases/download/all-userstyles-export/import.json')
    args = parser.parse_args()
    try:
        if args.command == 'build':
            build(args.config, args.output, args.cache)
        elif args.command == 'examine':
            print(json.dumps(inspect(load_json(args.file)), indent=2))
        elif args.command == 'check':
            report = load_json(args.output / 'build-report.json')
            if set(report['artifacts']) != {'import.json', 'lib.less'}:
                raise ValueError('Unexpected artifact set')
            for name, checksum in report['artifacts'].items():
                if digest((args.output / name).read_bytes()) != checksum:
                    raise ValueError(f'Generated artifact changed: {name}; rebuild before import')
            summary = inspect(load_json(args.output / 'import.json'))
            if summary != report['summary'] or summary['imports'] or summary['update_urls']:
                raise ValueError('Generated export failed safety checks')
            print(f'Checked {summary["styles"]} styles; compiler/browser validation is separate.')
        else:
            update(args.vendor_dir, args.commit, args.export_url)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'achroma-stylus: {error}\n')


if __name__ == '__main__':
    main()
