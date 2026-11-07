"""Default filter-lock regressions for the inherited Linux/macOS libm divergence."""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'applications/stylus'))
import filters

spec = importlib.util.spec_from_file_location('lock_producer', ROOT / 'tools/build.py')
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
LOCK = ROOT / 'applications/stylus/filters.lock.json'
REVISION = '41572a8510f6ce8f567b12371d91016eec1a90f6'


class FilterLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.palettes = producer.stylus.resolve_palettes(
            {v: json.loads((ROOT / f'palette/{v}.json').read_text()) for v in ('dark', 'light')},
            json.loads((ROOT / 'applications/stylus/mapping.json').read_text()))
        self.lock = json.loads(LOCK.read_text())
        self.path = self.root / 'filters.lock.json'

    def reject(self, mutate, message):
        value = copy.deepcopy(self.lock)
        mutate(value)
        self.path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, message):
            filters.locked(self.palettes, self.path)

    def test_exact_coverage_and_approved_provenance(self):
        fitted = filters.locked(self.palettes, LOCK)
        self.assertEqual(set(fitted), {v for p in self.palettes.values() for v in p.values()})
        self.assertEqual(len(fitted), 52)
        baseline = json.loads((ROOT / 'fixtures/extraction/stylus.json').read_text())
        self.assertEqual(self.lock['provenance']['nativeArtifacts'], baseline['artifacts'])
        self.assertEqual(self.lock['provenance']['sourceRevision'], REVISION)
        self.assertEqual(self.lock['provenance']['sourceArchiveSha256'],
                         '0a1c0b12a81ea226d5b79b43f9ddb6a651df467df353d5ebfab93833ba064c7a')

    def test_missing_duplicate_and_stale_lock_fail_closed(self):
        with self.assertRaises(FileNotFoundError):
            filters.locked(self.palettes, self.path)
        self.path.write_text(LOCK.read_text().replace('"schemaVersion": 1,',
                                                     '"schemaVersion": 1, "schemaVersion": 1,'))
        with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
            filters.locked(self.palettes, self.path)
        self.reject(lambda lock: lock.update(resolvedPalettesSha256='0' * 64), 'stale resolved')
        # Same color set is insufficient: the lock also binds variant/role assignments.
        self.palettes['light']['green'], self.palettes['light']['red'] = (
            self.palettes['light']['red'], self.palettes['light']['green'])
        with self.assertRaisesRegex(ValueError, 'stale resolved'):
            filters.locked(self.palettes, LOCK)

    def test_schema_provenance_and_coverage_rejected(self):
        for mutate, message in (
            (lambda x: x.update(schemaVersion=True), 'schema version'),
            (lambda x: x.update(fitterVersion=2), 'fitter version'),
            (lambda x: x.update(extra='ignored'), 'unexpected fields'),
            (lambda x: x.update(provenance=[]), 'provenance'),
            (lambda x: x['provenance'].update(sourceArchiveSha256='bad'), 'invalid digest'),
            (lambda x: x['provenance'].update(runtime=False), 'invalid runtime'),
            (lambda x: x['provenance']['nativeArtifacts'].pop('lib.less'), 'native artifacts'),
            (lambda x: x['filters'].pop('#4f6b4f'), 'coverage'),
            (lambda x: x['filters'].update({'#ffffff': x['filters']['#4f6b4f']}), 'coverage'),
        ):
            with self.subTest(message=message):
                self.reject(mutate, message)

    def test_parameter_shape_types_bounds_and_quantization_rejected(self):
        for parameters in (None, {}, [], [0] * 5, [0] * 7, [True] * 6,
                           ['1'] * 6, [float('nan')] * 6, [float('inf')] * 6,
                           [-1] * 6, [101, 0, 100, 0, 100, 100],
                           [0, 0, 8001, 0, 100, 100], [0, 0, 100, 361, 100, 100],
                           [0, 0, 100, 0, 201, 100], [0.123456, 0, 100, 0, 100, 100]):
            with self.subTest(parameters=parameters):
                self.reject(lambda x: x['filters']['#4f6b4f'].update(parameters=parameters),
                            'six parameters|invalid rounded parameter')

    def test_emitted_filter_error_is_recomputed_not_trusted(self):
        self.reject(lambda x: x['filters']['#4f6b4f'].update(parameters=[0, 0, 100, 0, 100, 100]),
                    'exceeds channel tolerance')
        for error in (False, None, '0.478', -1, 9, float('nan'), float('inf')):
            with self.subTest(error=error):
                self.reject(lambda x: x['filters']['#4f6b4f'].update(maxChannelError=error),
                            'invalid reported error')
        self.reject(lambda x: x['filters']['#4f6b4f'].update(maxChannelError=0.0),
                    'reported error disagrees')

    def test_linux_sin_ulp_changes_custom_search_but_not_locked_default_build(self):
        # First differing trial from the actual macOS/Linux traces, with saturation
        # zero: a one-ULP sin difference flips a spurious hue-improvement decision.
        angle = float.fromhex('0x1.4e2746ef4e6f0p+1')
        linux_sin = float.fromhex('0x1.034878b9b6c0cp-1')
        original_sin = filters.math.sin
        approved = filters.locked(self.palettes, LOCK)['#4f6b4f']['css']
        with patch.object(filters.math, 'sin', side_effect=lambda x: linux_sin if x == angle else original_sin(x)):
            self.assertNotEqual(filters.fit('#4f6b4f')['css'], approved)
            with patch.object(filters, 'fit', side_effect=AssertionError('Defaults must not invoke fitter')):
                producer.build(self.root / 'output', self.root / 'cache', '0.1.0-dev', REVISION)
        report = json.loads((self.root / 'output/payload/reports/stylus-build.json').read_text())
        baseline = json.loads((ROOT / 'fixtures/extraction/stylus.json').read_text())
        self.assertEqual(report['artifacts'], baseline['artifacts'])
        self.assertEqual(report['filters']['#4f6b4f']['css'], approved)
        manifest = json.loads((self.root / 'output/payload/manifest.json').read_text())
        self.assertEqual(manifest['buildInputs']['applications/stylus/filters.lock.json'],
                         producer.stylus.digest(LOCK.read_bytes()))

    def test_invalid_lock_cannot_reuse_previously_successful_native_output(self):
        config = self.root / 'config'
        config.mkdir()
        (config / 'palette.json').write_text(json.dumps(
            {v: json.loads((ROOT / f'palette/{v}.json').read_text()) for v in ('dark', 'light')}))
        for name in ('mapping.json', 'filters.lock.json'):
            (config / name).write_bytes((ROOT / 'applications/stylus' / name).read_bytes())
        shutil.copytree(ROOT / 'applications/stylus/vendor', config / 'vendor')
        output = self.root / 'native'
        producer.stylus.build(config, output, self.root / 'cache')
        before = (output / 'import.json').read_bytes()
        (config / 'filters.lock.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Filter lock'):
            producer.stylus.build(config, output, self.root / 'cache')
        self.assertEqual(before, (output / 'import.json').read_bytes())
        (config / 'filters.lock.json').unlink()
        with self.assertRaises(FileNotFoundError):
            producer.stylus.build(config, output, self.root / 'cache')
        self.assertEqual(before, (output / 'import.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
