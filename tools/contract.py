"""Explicit v1 pilot contract checks shared by producer and archive verifier."""

import math
from pathlib import PurePosixPath
import re

BROWSER_ROLES = tuple(('rosewater flamingo pink mauve red maroon peach yellow green teal sky '
                       'sapphire blue lavender text subtext1 subtext0 overlay2 overlay1 overlay0 '
                       'surface2 surface1 surface0 base mantle crust').split())
ACCENTS = BROWSER_ROLES[:14]
PALETTE_ROLES = BROWSER_ROLES + tuple(('mono00 mono04 mono06 mono08 mono10 mono12 mono14 '
                                     'mono16 mono18 mono20 mono22 mono23 mono24 mono25 '
                                     'mixRed10 mixRed25 mixGreen10 mixGreen25 mixMauve25 '
                                     'mixBlue25 mixSky25 mixPeach25').split()) + tuple(
    f'{prefix}{number:02}' for prefix in ('acc', 'accDim') for number in range(9))
FLAVORS = {'dark': 'mocha', 'light': 'latte'}
STYLE_COUNT = 132
FORMAT = 'Stylus UserCSS backup with Less sources'
COMPATIBILITY = 'Stylus Less parens-division; browser import not automatically tested'
LICENSE_PATHS = {f'licenses/catppuccin-{name}-MIT.txt'
                 for name in ('highlightjs', 'prismjs', 'python', 'userstyles')} | {'licenses/provenance.json'}
VENDOR_NAMES = {'LICENSE', 'export.json', 'highlightjs-important.css', 'highlightjs.css',
                'prism.css', 'pygments.css', 'std.less'}
BUILD_INPUT_PATHS = ({'tools/build.py', 'tools/contract.py', 'schemas/consumer.schema.json',
                      'schemas/palette.schema.json', 'applications/stylus/build.py',
                      'applications/stylus/filters.py', 'applications/stylus/mapping.json'}
                     | {f'palette/{v}.json' for v in FLAVORS}
                     | {f'applications/stylus/vendor/{name}' for name in VENDOR_NAMES | {'upstream.lock.json'}}
                     | LICENSE_PATHS)
ARTIFACT_PATHS = ({'data/consumer.json', 'reports/stylus-build.json',
                   'themes/stylus/import.json', 'themes/stylus/lib.less'} | LICENSE_PATHS
                  | {f'{kind}/{v}.{ext}' for v in FLAVORS for kind, ext in
                     (('palette', 'json'), ('mappings/stylus', 'json'), ('fragments/stylus', 'less'))})
IDENTIFIER = r'(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)'
VERSION_PATTERN = (r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
                   + rf'(?:-{IDENTIFIER}(?:\.{IDENTIFIER})*)?')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def object_keys(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), f'{label}: unexpected fields')


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label}: expected nonempty string')


def digest(value, label):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None,
            f'{label}: expected SHA-256')


def source_revision(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value) is not None,
            'release: expected full source revision SHA')


def validate_release(value):
    object_keys(value, ('version', 'sourceRevision'), 'release')
    require(isinstance(value['version'], str) and re.fullmatch(VERSION_PATTERN, value['version']) is not None,
            'release: expected semantic version without v prefix or build metadata')
    source_revision(value['sourceRevision'])


def color_map(value, keys, label):
    object_keys(value, keys, label)
    require(all(isinstance(c, str) and re.fullmatch('#[0-9a-f]{6}', c) for c in value.values()),
            f'{label}: colors must be lowercase #rrggbb')


def validate_palette(value, keys=PALETTE_ROLES):
    require(set(keys) == set(PALETTE_ROLES), 'Palette schema role keys differ from contract')
    color_map(value, PALETTE_ROLES, 'palette')


def validate_mapping(value):
    object_keys(value, ('accent', 'roles'), 'source mapping')
    require(isinstance(value['accent'], str) and value['accent'] in ACCENTS, 'Invalid Stylus accent role')
    require(isinstance(value['roles'], dict) and set(value['roles']) <= set(BROWSER_ROLES),
            'Unknown browser roles')
    require(all(isinstance(role, str) and role in PALETTE_ROLES for role in value['roles'].values()),
            'Mapping references must be palette role names')


def validate_settings(value):
    object_keys(value, ('updateInterval',), 'mapping settings')
    require(type(value['updateInterval']) is int and value['updateInterval'] == 0,
            'Unexpected Stylus global update policy')


def validate_resolved_mapping(value, variant):
    object_keys(value, ('flavor', 'palette', 'usercssVariables', 'settings'), 'Stylus mapping')
    require(value['flavor'] == FLAVORS[variant], 'Incorrect variant flavor')
    color_map(value['palette'], BROWSER_ROLES, 'resolved palette')
    variables = value['usercssVariables']
    object_keys(variables, ('lightFlavor', 'darkFlavor', 'accentColor'), 'Stylus variables')
    require(variables['lightFlavor'] == 'latte' and variables['darkFlavor'] == 'mocha',
            'Incorrect Stylus flavor defaults')
    require(isinstance(variables['accentColor'], str) and variables['accentColor'] in ACCENTS,
            'Invalid Stylus accent default')
    validate_settings(value['settings'])


def validate_consumer(value):
    object_keys(value, ('schemaVersion', 'release', 'palettes', 'mappings'), 'consumer')
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1, 'Unsupported consumer schema')
    validate_release(value['release'])
    object_keys(value['palettes'], FLAVORS, 'consumer palette variants')
    object_keys(value['mappings'], ('stylus',), 'consumer applications')
    object_keys(value['mappings']['stylus'], FLAVORS, 'consumer mapping variants')
    for variant in FLAVORS:
        validate_palette(value['palettes'][variant])
        validate_resolved_mapping(value['mappings']['stylus'][variant], variant)
    require(value['mappings']['stylus']['dark']['usercssVariables'] ==
            value['mappings']['stylus']['light']['usercssVariables'], 'Variant variable defaults disagree')


def hash_map(value, keys, label):
    object_keys(value, keys, label)
    for name, checksum in value.items():
        path = PurePosixPath(name)
        require(not path.is_absolute() and '..' not in path.parts and str(path) == name,
                f'{label}: unsafe path')
        digest(checksum, f'{label}.{name}')


def validate_manifest(value):
    object_keys(value, ('schemaVersion', 'release', 'applications', 'buildInputs', 'artifacts'), 'manifest')
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1, 'Unsupported manifest schema')
    validate_release(value['release'])
    object_keys(value['applications'], ('stylus',), 'manifest applications')
    app = value['applications']['stylus']
    object_keys(app, ('format', 'compatibility', 'nativeNames', 'styles', 'flavors'), 'manifest Stylus metadata')
    require(app['format'] == FORMAT and app['compatibility'] == COMPATIBILITY, 'Unsupported Stylus compatibility metadata')
    require(type(app['styles']) is int and app['styles'] == STYLE_COUNT, 'Unexpected manifest style count')
    require(app['flavors'] == FLAVORS, 'Unexpected manifest flavors')
    names = app['nativeNames']
    require(isinstance(names, list) and len(names) == STYLE_COUNT, 'Unexpected manifest native names')
    for name in names:
        text(name, 'native name')
    require(len(set(names)) == STYLE_COUNT, 'Duplicate native names')
    hash_map(value['buildInputs'], BUILD_INPUT_PATHS, 'manifest build inputs')
    hash_map(value['artifacts'], ARTIFACT_PATHS, 'manifest artifacts')


def validate_report(value, consumer):
    object_keys(value, ('schema', 'fingerprint', 'upstream', 'summary', 'excluded_styles',
                        'palettes', 'filters', 'artifacts', 'validation'), 'build report')
    require(type(value['schema']) is int and value['schema'] == 1, 'Unsupported build report schema')
    digest(value['fingerprint'], 'report fingerprint')
    text(value['validation'], 'report validation')
    hash_map(value['artifacts'], ('import.json', 'lib.less'), 'report artifacts')
    object_keys(value['palettes'], FLAVORS, 'report palette variants')
    for variant in FLAVORS:
        color_map(value['palettes'][variant], BROWSER_ROLES, 'report palette')
        require(value['palettes'][variant] == consumer['mappings']['stylus'][variant]['palette'],
                'Mapping/native build palette mismatch')
    upstream = value['upstream']
    object_keys(upstream, ('schema', 'standard_commit', 'note', 'files'), 'upstream lock')
    require(type(upstream['schema']) is int and upstream['schema'] == 1, 'Unsupported upstream lock schema')
    source_revision(upstream['standard_commit'])
    text(upstream['note'], 'upstream note')
    object_keys(upstream['files'], VENDOR_NAMES, 'upstream files')
    for name, record in upstream['files'].items():
        object_keys(record, ('url', 'sha256'), 'upstream file')
        require(isinstance(record['url'], str) and record['url'].startswith('https://'), 'Invalid upstream URL')
        digest(record['sha256'], 'upstream checksum')
    object_keys(value['excluded_styles'], ('Codeberg Catppuccin', 'PythonAnywhere Catppuccin'), 'excluded styles')
    for reason in value['excluded_styles'].values():
        text(reason, 'exclusion reason')
    colors = {color for p in value['palettes'].values() for color in p.values()}
    object_keys(value['filters'], colors, 'report filters')
    for record in value['filters'].values():
        object_keys(record, ('css', 'max_channel_error'), 'filter diagnostic')
        text(record['css'], 'filter css')
        error = record['max_channel_error']
        require(type(error) in (int, float) and math.isfinite(error) and 0 <= error <= 8,
                'Invalid filter error')
    summary = value['summary']
    object_keys(summary, ('styles', 'settings_records', 'imports', 'update_urls', 'light_flavors',
                          'dark_flavors', 'accents'), 'report summary')
    require(type(summary['styles']) is int and summary['styles'] == STYLE_COUNT, 'Unexpected report style count')
    require(type(summary['settings_records']) is int and summary['settings_records'] == 1,
            'Unexpected report settings count')
    expected = {'imports': [], 'update_urls': [], 'light_flavors': ['latte'], 'dark_flavors': ['mocha'],
                'accents': [consumer['mappings']['stylus']['dark']['usercssVariables']['accentColor']]}
    require(all(summary[key] == item for key, item in expected.items()), 'Unexpected report defaults or safety summary')
