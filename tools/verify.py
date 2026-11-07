"""Verify a local producer archive without extraction or third-party packages."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract


def json_object(pairs):
    result = {}
    for key, value in pairs:
        contract.require(key not in result, f'Duplicate JSON field: {key}')
        result[key] = value
    return result


def validate_native(records, manifest, report, consumer):
    contract.require(isinstance(records, list), 'Native export must be an array')
    variables = consumer['mappings']['stylus']['dark']['usercssVariables']
    names = []
    settings_records = 0
    seen = {key: set() for key in variables}
    for record in records:
        contract.require(isinstance(record, dict), 'Native record must be an object')
        if 'sourceCode' not in record:
            contract.object_keys(record, ('settings',), 'native settings record')
            settings = record['settings']
            contract.require(isinstance(settings, dict), 'Native settings must be an object')
            contract.validate_settings({'updateInterval': settings.get('updateInterval')})
            settings_records += 1
            continue
        contract.require('settings' not in record, 'Style must not contain global settings')
        contract.text(record.get('name'), 'native style name')
        names.append(record['name'])
        source = record['sourceCode']
        contract.text(source, 'native source')
        contract.require(type(record.get('enabled')) is bool, 'Native enabled flag must be boolean')
        metadata = record.get('usercssData')
        contract.require(isinstance(metadata, dict) and metadata.get('preprocessor') == 'less',
                         'Native style must declare Less preprocessing')
        contract.require(not any(key in record for key in ('sections', 'originalDigest', 'updateUrl', 'updateURL'))
                         and not any(key in metadata for key in ('updateUrl', 'updateURL'))
                         and not re.search(r'@import\b|^\s*@updateURL\b', source, re.M | re.I),
                         'Native export contains stale or unsafe fields/imports')
        saved = metadata.get('vars')
        contract.require(isinstance(saved, dict) and set(variables) <= set(saved),
                         'Native style is missing variable defaults')
        for key, expected in variables.items():
            variable = saved[key]
            contract.require(isinstance(variable, dict) and variable.get('type') == 'select',
                             f'Native {key}: expected select variable')
            contract.require(variable.get('value') == expected, f'Native {key}: incorrect saved default')
            options = variable.get('options')
            contract.require(isinstance(options, list) and bool(options), f'Native {key}: missing options')
            option_names = []
            for option in options:
                contract.require(isinstance(option, dict), f'Native {key}: invalid option')
                contract.text(option.get('name'), 'option name')
                contract.text(option.get('value'), 'option value')
                option_names.append(option['name'])
            # Upstream exposes subtext0 as an extra native select option; the
            # producer's configurable default remains one of the 14 accent roles.
            allowed = contract.ACCENTS + ('subtext0',) if key == 'accentColor' else ('latte', 'frappe', 'macchiato', 'mocha')
            contract.require(len(set(option_names)) == len(option_names) and set(option_names) == set(allowed),
                             f'Native {key}: unsupported options')
            contract.require(variable.get('default') in allowed, f'Native {key}: invalid upstream default')
            if key != 'accentColor':
                contract.require(variable['default'] == expected, f'Native {key}: incorrect flavor default')
            contract.require(all(option['value'] == option['name'] for option in options),
                             f'Native {key}: option values disagree with role identifiers')
            seen[key].add(variable['value'])
    app = manifest['applications']['stylus']
    contract.require(names == app['nativeNames'] and len(names) == app['styles'],
                     'Native names/count disagree with manifest')
    summary = {'styles': len(names), 'settings_records': settings_records, 'imports': [], 'update_urls': [],
               'light_flavors': sorted(seen['lightFlavor']), 'dark_flavors': sorted(seen['darkFlavor']),
               'accents': sorted(seen['accentColor'])}
    contract.require(summary == report['summary'], 'Native settings/count/defaults disagree with report')


def verify(archive, sums):
    archive, sums = Path(archive), Path(sums)
    expected = sums.read_text(encoding='utf-8').strip().split('  ')
    if len(expected) != 2 or expected[1] != archive.name or not re.fullmatch('[0-9a-f]{64}', expected[0]):
        raise ValueError('Invalid checksum file or archive filename')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected[0]:
        raise ValueError('Archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        contract.require(len(names) == len(set(names)), 'Duplicate archive members')
        for entry in z.infolist():
            path = PurePosixPath(entry.filename)
            contract.require(not path.is_absolute() and '..' not in path.parts and '\\' not in entry.filename
                             and ':' not in entry.filename and str(path) == entry.filename
                             and stat.S_ISREG(entry.external_attr >> 16),
                             f'Unsafe archive member: {entry.filename}')

        def load(name):
            return json.loads(z.read(name), object_pairs_hook=json_object)

        manifest = load('manifest.json')
        contract.validate_manifest(manifest)
        contract.require(archive.name == f'achroma-{manifest["release"]["version"]}.zip',
                         'Release/archive version mismatch')
        contract.require(set(names) == {'manifest.json', *manifest['artifacts']}, 'Archive/manifest member mismatch')
        for name, checksum in manifest['artifacts'].items():
            contract.require(hashlib.sha256(z.read(name)).hexdigest() == checksum,
                             f'Artifact checksum mismatch: {name}')
        consumer = load('data/consumer.json')
        contract.validate_consumer(consumer)
        contract.require(consumer['release'] == manifest['release'], 'Consumer/manifest identity mismatch')
        report = load('reports/stylus-build.json')
        contract.validate_report(report, consumer)
        for variant in contract.FLAVORS:
            palette = load(f'palette/{variant}.json')
            mapping = load(f'mappings/stylus/{variant}.json')
            contract.validate_palette(palette)
            contract.validate_resolved_mapping(mapping, variant)
            contract.require(palette == consumer['palettes'][variant]
                             and mapping == consumer['mappings']['stylus'][variant],
                             'Aggregate/individual data mismatch')
            fragment = ''.join(f'@{key}: {color};\n' for key, color in mapping['palette'].items())
            contract.require(z.read(f'fragments/stylus/{variant}.less').decode('utf-8') == fragment,
                             'Fragment/mapping palette mismatch')
        for name, checksum in report['artifacts'].items():
            contract.require(manifest['artifacts'][f'themes/stylus/{name}'] == checksum,
                             'Report/native hash mismatch')
        contract.text(z.read('themes/stylus/lib.less').decode('utf-8'), 'native library')
        validate_native(load('themes/stylus/import.json'), manifest, report, consumer)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('sums', type=Path)
    args = parser.parse_args()
    try:
        manifest = verify(args.archive, args.sums)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f'achroma-verify: {error}\n')
    print(f'Verified {len(manifest["artifacts"])} artifacts; integrity is not authenticity.')


if __name__ == '__main__':
    main()
