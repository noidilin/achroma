"""Run from any shell: python -B -m unittest discover -s tests/stylus."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'applications/stylus'
sys.path.insert(0, str(CONFIG))
import build
import filters


def fixture(url='https://userstyles.catppuccin.com/lib/std/v1.less'):
    variables = {}
    for name, value in [('lightFlavor', 'latte'), ('darkFlavor', 'mocha'), ('accentColor', 'rosewater')]:
        variables[name] = {'type': 'select', 'value': None, 'default': value,
                           'options': [{'name': value, 'value': value}]}
    return [{'settings': {'updateInterval': 24, 'unknown': True}}, {
        'name': 'Fixture', 'enabled': False, 'custom': {'included': ['example.test']},
        'updateUrl': 'https://example.test/upstream', 'originalDigest': 'old',
        'sections': [{'code': 'stale compiled CSS'}],
        'usercssData': {'preprocessor': 'less', 'updateURL': 'https://example.test/upstream',
                        'vars': variables},
        'sourceCode': f'/* ==UserStyle==\n@updateURL https://example.test/upstream\n==/UserStyle== */\n'
                      f'@import "{url}";\n@-moz-document domain("example.test") {{body {{color: @text;}}}}',
    }]


class TransformTests(unittest.TestCase):
    def test_all_standard_urls(self):
        for url in build.STANDARD_URLS:
            with self.subTest(url=url):
                data = build.transform(fixture(url), '@text: #123456;', 'rosewater')
                self.assertIn('@text: #123456;', data[1]['sourceCode'])
                self.assertFalse(build.inspect(data)['imports'])
                self.assertFalse(build.inspect(data)['update_urls'])

    def test_metadata_and_unknown_fields(self):
        original = fixture()
        data = build.transform(original, '', 'rosewater')
        self.assertEqual(data[0]['settings'], {'updateInterval': 0, 'unknown': True})
        self.assertFalse(data[1]['enabled'])
        self.assertEqual(data[1]['custom'], original[1]['custom'])
        self.assertNotIn('sections', data[1])
        self.assertNotIn('originalDigest', data[1])
        self.assertEqual(original, fixture())
        self.assertEqual(build.inspect(data)['light_flavors'], ['latte'])
        self.assertEqual(build.inspect(data)['dark_flavors'], ['mocha'])

    def test_optional_vars(self):
        data = fixture()
        data[1]['usercssData']['vars'] = {}
        build.transform(data, '', 'rosewater')

    def test_invalid_accent(self):
        with self.assertRaisesRegex(ValueError, 'does not support'):
            build.transform(fixture(), '', 'not-a-color')

    def test_unknown_dependency_fails(self):
        for url in ('https://example.test/new.less', 'https://userstyles.catppuccin.com/lib/std/v2.less'):
            with self.assertRaises(ValueError):
                build.transform(fixture(url), '', 'rosewater')

    def test_css_import_bundled(self):
        data = fixture()
        data[1]['sourceCode'] += '\n@import url("https://example.test/a.css");'
        out = build.transform(data, '', 'rosewater', {'https://example.test/a.css': '.a {color: var(--ctp-text);} '})
        self.assertIn('.a {color:', out[1]['sourceCode'])
        self.assertFalse(build.inspect(out)['imports'])

    def test_unrecognized_import_syntax_fails(self):
        data = fixture()
        data[1]['sourceCode'] += '\n@import url(foo.css);'
        with self.assertRaisesRegex(ValueError, 'unresolved import'):
            build.transform(data, '', 'rosewater')

    def test_media_import_fails(self):
        data = fixture()
        data[1]['sourceCode'] += '\n@import (css) url("a.css") (prefers-color-scheme: light);'
        with self.assertRaisesRegex(ValueError, 'unsupported dependency'):
            build.transform(data, '', 'rosewater', {'a.css': ''})

    def test_non_usercss_record_fails(self):
        with self.assertRaisesRegex(ValueError, 'non-UserCSS'):
            build.transform([{'sections': []}], '', 'rosewater')


class PaletteTests(unittest.TestCase):
    def palettes(self):
        return {variant: {role: '#808080' for role in build.ROLES} for variant in ('light', 'dark')}

    def test_browser_mapping(self):
        palettes = self.palettes()
        for palette in palettes.values():
            palette['acc07'] = '#dad5c8'
            palette['acc06'] = '#c0baad'
        resolved = build.resolve_palettes(palettes, build.load_json(CONFIG / 'mapping.json'))
        self.assertEqual(resolved['dark']['rosewater'], '#dad5c8')
        self.assertEqual(resolved['light']['flamingo'], '#c0baad')

    def test_invalid_palettes(self):
        for bad in (None, '#fff', '#gggggg', 12):
            palettes = self.palettes()
            palettes['light']['base'] = bad
            with self.assertRaises(ValueError):
                build.resolve_palettes(palettes, {})

    def test_unknown_mapping(self):
        with self.assertRaisesRegex(ValueError, 'Unknown browser roles'):
            build.resolve_palettes(self.palettes(), {'roles': {'typo': 'base'}})

    def test_library_replaces_only_latte_mocha(self):
        _, inputs = build.vendor_inputs(CONFIG / 'vendor')
        palettes = self.palettes()
        library = build.make_library(inputs['std.less'].decode(), palettes,
                                     {'#808080': filters.fit('#808080')})
        self.assertIn('@base: #808080;', library)
        self.assertIn('@base: #303446;', library)  # Frappé untouched
        self.assertIn('@base: #24273a;', library)  # Macchiato untouched
        self.assertNotIn('@base: #eff1f5;', library)
        self.assertNotIn('@base: #1e1e2e;', library)
        self.assertIn('color-scheme: if(@flavor = latte, light, dark)', library)

    def test_library_api_drift_fails(self):
        with self.assertRaisesRegex(ValueError, 'Expected one'):
            build.replace_flavor('@new-map: {};', 'catppuccin', 'latte', '')

    def test_filters_deterministic_and_within_tolerance(self):
        for color in ('#808080', '#dad5c8', '#778777', '#9b5f5f', '#4a6480'):
            with self.subTest(color=color):
                first = filters.fit(color)
                self.assertEqual(first, filters.fit(color))
                self.assertLessEqual(first['max_channel_error'], filters.MAX_ERROR)
        self.assertLess(filters.fit('#808080')['max_channel_error'], .001)

    def test_black_and_identity_filter_math(self):
        self.assertEqual(filters.apply([0, 0, 1, 0, 1, 1]), [0, 0, 0])
        self.assertEqual(filters.apply([1, 0, 1, 0, 1, 1]), [255, 255, 255])


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'config'
        self.config.mkdir()
        (self.config / 'mapping.json').write_bytes(b'{"accent":"rosewater"}')
        (self.config / 'palette.json').write_bytes(build.json_bytes(PaletteTests().palettes()))
        vendor = self.config / 'vendor'
        vendor.mkdir()
        for name in [*build.CSS_URLS, 'export.json', 'std.less', 'LICENSE', 'upstream.lock.json']:
            (vendor / name).write_bytes((CONFIG / 'vendor' / name).read_bytes())
        self.output = self.root / 'output'
        self.cache = self.root / 'cache'

    def run_build(self):
        # This synthetic gray palette is deliberately not the locked default.
        build.build(self.config, self.output, self.cache, fit_custom_colors=True)

    def test_real_export_and_reproducibility(self):
        self.run_build()
        first = (self.output / 'import.json').read_bytes()
        report = build.load_json(self.output / 'build-report.json')
        self.assertEqual(report['summary']['styles'], 132)
        self.assertEqual(set(report['excluded_styles']),
                         {'Codeberg Catppuccin', 'PythonAnywhere Catppuccin'})
        mtime = (self.output / 'import.json').stat().st_mtime_ns
        self.run_build()
        self.assertEqual(mtime, (self.output / 'import.json').stat().st_mtime_ns)
        (self.output / 'import.json').unlink()
        self.run_build()
        self.assertEqual(first, (self.output / 'import.json').read_bytes())
        self.assertFalse(report['summary']['imports'])
        self.assertFalse(report['summary']['update_urls'])

    def test_snips_chroma_is_explicitly_excluded_from_refresh_and_build(self):
        vendor = self.config / 'vendor'
        lock, inputs = build.vendor_inputs(vendor)
        records = json.loads(inputs['export.json'])
        snips = fixture()[1]
        snips['name'] = 'snips.sh Catppuccin'
        snips['sourceCode'] += ('\n@import (css) '
                               'url("https://chroma.catppuccin.com/@{lightFlavor}-chroma-style.css") '
                               '(prefers-color-scheme: light);')
        # The dependency remains unsupported in general, not silently stripped.
        with self.assertRaisesRegex(ValueError, 'unsupported dependency'):
            build.transform([snips], '', 'rosewater')
        inputs['export.json'] = build.json_bytes(records + [snips])
        urls = {entry['url']: inputs[name] for name, entry in lock['files'].items()}
        with patch.object(build, 'download', side_effect=urls.__getitem__):
            build.update(vendor, lock['standard_commit'], lock['files']['export.json']['url'])
        self.run_build()
        report = build.load_json(self.output / 'build-report.json')
        self.assertEqual(report['summary']['styles'], 132)
        self.assertEqual(report['excluded_styles']['snips.sh Catppuccin'],
                         'Imports precompiled Chroma themes with hardcoded colors.')
        self.assertEqual(set(report['excluded_styles']), set(build.EXCLUDED))
        self.assertNotIn('snips.sh Catppuccin',
                         {style.get('name') for style in build.load_json(self.output / 'import.json')})

    def test_failure_preserves_previous_output(self):
        self.run_build()
        before = (self.output / 'import.json').read_bytes()
        (self.config / 'vendor/std.less').write_text('corrupted')
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
            self.run_build()
        self.assertEqual(before, (self.output / 'import.json').read_bytes())

    def test_changed_palette_rebuilds(self):
        self.run_build()
        before = (self.output / 'import.json').read_bytes()
        palettes = PaletteTests().palettes()
        palettes['light']['base'] = '#ededed'
        (self.config / 'palette.json').write_bytes(build.json_bytes(palettes))
        self.run_build()
        self.assertNotEqual(before, (self.output / 'import.json').read_bytes())

    def test_cli_requires_explicit_paths(self):
        result = subprocess.run([sys.executable, '-B', str(CONFIG / 'build.py'), 'build'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        for option in ('--config', '--output', '--cache'):
            self.assertIn(option, result.stderr)

    def test_rejects_non_commit_update_before_network(self):
        with self.assertRaises(ValueError):
            build.update(self.root / 'vendor', 'main', 'https://example.test/export')

    def test_standalone_cli_preserves_explicit_paths(self):
        for name in ('build.py', 'filters.py'):
            shutil.copyfile(CONFIG / name, self.config / name)
        output = self.root / 'output with spaces'
        env = dict(os.environ, HOME=str(self.root / 'empty home'),
                   XDG_CONFIG_HOME=str(self.root / 'unused config'),
                   XDG_DATA_HOME=str(self.root / 'unused data'),
                   XDG_CACHE_HOME=str(self.root / 'unused cache'))
        subprocess.run([sys.executable, '-B', str(self.config / 'build.py'), 'build',
                        '--config', str(self.config), '--output', str(output),
                        '--cache', str(self.cache), '--fit-custom-colors'], env=env, check=True)
        self.assertTrue((output / 'import.json').exists())
        self.assertFalse((self.root / 'unused data').exists())


if __name__ == '__main__':
    unittest.main()
