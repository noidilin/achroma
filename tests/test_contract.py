"""Source-named regressions for the bounded standalone producer contract."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


producer = module('producer', ROOT / 'tools/build.py')
verifier = module('verifier', ROOT / 'tools/verify.py')
stylus = producer.stylus
REVISION = json.loads((ROOT / 'fixtures/extraction/provenance.json').read_text())['achromaBaseline']


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.output = cls.root / 'release'
        producer.build(cls.output, cls.root / 'cache', '0.1.0-dev', REVISION)
        cls.payload = cls.output / 'payload'
        cls.archive = cls.output / 'achroma-0.1.0-dev.zip'

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_palette_matches_mechanical_extraction(self):
        baseline = stylus.load_json(ROOT / 'fixtures/extraction/palette.json')
        keys = stylus.load_json(ROOT / 'schemas/palette.schema.json')['required']
        for variant in ('dark', 'light'):
            palette = stylus.load_json(ROOT / f'palette/{variant}.json')
            self.assertEqual(palette, baseline[variant])
            self.assertEqual(len(palette), 66)
            producer.validate_palette(palette, keys)
            self.assertEqual(palette, stylus.load_json(self.payload / f'palette/{variant}.json'))

    def test_palette_and_mapping_validation(self):
        palette = stylus.load_json(ROOT / 'palette/dark.json')
        for bad in ({}, {**palette, 'extra': '#ffffff'}, {**palette, 'base': 'reset'},
                    {**palette, 'base': '#ABCDEF'}):
            with self.assertRaises(ValueError):
                producer.validate_palette(bad, palette)
        for bad in ({}, {'accent': 'invalid', 'roles': {}},
                    {'accent': 'rosewater', 'roles': {'base': 3}}):
            with self.assertRaises(ValueError):
                producer.validate_mapping(bad)

    def test_real_native_bytes_match_baseline(self):
        baseline = stylus.load_json(ROOT / 'fixtures/extraction/stylus.json')
        report = stylus.load_json(self.payload / 'reports/stylus-build.json')
        self.assertEqual(report['artifacts'], baseline['artifacts'])
        self.assertEqual(report['summary'], baseline['summary'])
        self.assertEqual(report['excluded_styles'], baseline['excluded_styles'])
        for name, digest in baseline['artifacts'].items():
            self.assertEqual(stylus.digest((self.payload / 'themes/stylus' / name).read_bytes()), digest)
        report.pop('fingerprint')  # relocated generator changes provenance, never colors/settings/selectors
        self.assertEqual(stylus.digest(stylus.json_bytes(report)), baseline['reportWithoutFingerprintSha256'])
        self.assertLessEqual(max(f['max_channel_error'] for f in report['filters'].values()), .478)

    def test_resolved_mapping_fragment_and_native_have_one_palette(self):
        report = stylus.load_json(self.payload / 'reports/stylus-build.json')
        for variant, flavor in (('dark', 'mocha'), ('light', 'latte')):
            mapping = stylus.load_json(self.payload / f'mappings/stylus/{variant}.json')
            palette = stylus.load_json(ROOT / f'palette/{variant}.json')
            self.assertEqual(mapping['palette'], report['palettes'][variant])
            self.assertEqual(mapping['palette']['rosewater'], palette['acc07'])
            self.assertEqual(mapping['palette']['flamingo'], palette['acc06'])
            self.assertEqual(mapping['flavor'], flavor)
            self.assertEqual(mapping['settings'], {'updateInterval': 0})
            self.assertEqual(mapping['usercssVariables']['accentColor'], 'rosewater')
            self.assertEqual((self.payload / f'fragments/stylus/{variant}.less').read_text(),
                             ''.join(f'@{k}: {v};\n' for k, v in mapping['palette'].items()))

    def test_archive_hash_members_metadata_and_aggregate(self):
        manifest = verifier.verify(self.archive, self.output / 'SHA256SUMS')
        self.assertEqual(set(manifest['applications']), {'stylus'})
        self.assertEqual(len(manifest['applications']['stylus']['nativeNames']), 132)
        self.assertNotIn('manifest.json', manifest['artifacts'])
        with zipfile.ZipFile(self.archive) as z:
            self.assertEqual(z.namelist(), sorted(z.namelist()))
            self.assertNotIn('SHA256SUMS', z.namelist())
            for entry in z.infolist():
                self.assertEqual(entry.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(entry.external_attr >> 16, 0o100644)
                self.assertEqual(z.read(entry.filename), (self.payload / entry.filename).read_bytes())

    def test_optional_complement_manifest_extension_is_all_or_nothing(self):
        manifest = stylus.load_json(self.payload / 'manifest.json')
        contract = verifier.contract
        self.assertIn(contract.COMPLEMENT_ARTIFACT, manifest['artifacts'])
        self.assertTrue(contract.COMPLEMENT_INPUTS <= set(manifest['buildInputs']))
        contract.validate_manifest(manifest)
        manifest['artifacts'].pop(contract.COMPLEMENT_ARTIFACT)
        with self.assertRaisesRegex(ValueError, 'manifest build inputs'):
            contract.validate_manifest(manifest)
        for path in contract.COMPLEMENT_INPUTS:
            manifest['buildInputs'].pop(path)
        # Preserve support for the original v0.1.0 archive contract.
        contract.validate_manifest(manifest)

    def test_rehashed_complement_palette_tampering_is_rejected(self):
        with zipfile.ZipFile(self.archive) as original:
            entries = original.infolist()
            payload = {entry.filename: original.read(entry.filename) for entry in entries}
        name = verifier.contract.COMPLEMENT_ARTIFACT
        source = payload[name].decode().replace('--achroma-complement-base: #1e1e1e;',
                                               '--achroma-complement-base: #000000;')
        self.assertNotEqual(source.encode(), payload[name])
        payload[name] = source.encode()
        manifest = json.loads(payload['manifest.json'])
        manifest['artifacts'][name] = stylus.digest(payload[name])
        payload['manifest.json'] = stylus.json_bytes(manifest)
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            archive = Path(directory) / self.archive.name
            with zipfile.ZipFile(archive, 'w') as changed:
                for entry in entries:
                    changed.writestr(entry, payload[entry.filename])
            sums = Path(directory) / 'SHA256SUMS'
            sums.write_text(f'{stylus.digest(archive.read_bytes())}  {archive.name}\n')
            with self.assertRaisesRegex(ValueError, 'Complement palette differs'):
                verifier.verify(archive, sums)

    def test_report_and_consumer_forbid_personal_environment(self):
        for name in ('manifest.json', 'data/consumer.json', 'reports/stylus-build.json'):
            text = (self.payload / name).read_text()
            for forbidden in ('/Users/', '/home/', 'C:\\Users\\', str(self.root),
                              'achroma-current', 'ACHROMA_VARIANT', 'USERPROFILE', 'noidilin'):
                self.assertNotIn(forbidden, text)

    def test_consumer_exact_schema_fixture_and_individual_equality(self):
        consumer = stylus.load_json(self.payload / 'data/consumer.json')
        fixture = stylus.load_json(ROOT / 'fixtures/consumer/consumer.json')
        self.assertEqual(consumer, fixture)
        schema = stylus.load_json(ROOT / 'schemas/consumer.schema.json')
        self.assertEqual(set(consumer), set(schema['required']))
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(consumer['release']), {'version', 'sourceRevision'})
        self.assertEqual(set(consumer['release']), set(schema['properties']['release']['required']))
        for variant in ('dark', 'light'):
            self.assertEqual(consumer['palettes'][variant],
                             stylus.load_json(self.payload / f'palette/{variant}.json'))
            mapping = consumer['mappings']['stylus'][variant]
            self.assertEqual(mapping, stylus.load_json(self.payload / f'mappings/stylus/{variant}.json'))
            self.assertEqual(set(mapping), set(schema['$defs']['stylusMapping']['required']))
        # Archive URLs/checksums cannot be put inside the archive they identify.
        self.assertNotIn('archiveSha256', json.dumps(consumer))
        self.assertNotIn('archiveUrl', json.dumps(consumer))

    def test_frozen_legacy_library(self):
        expected = stylus.load_json(ROOT / 'fixtures/extraction/provenance.json')['legacyLibrarySha256']
        self.assertEqual(stylus.digest((ROOT / 'lib/lib.less').read_bytes()), expected)

    def test_plain_python_consumer_overrides(self):
        subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'fixtures/consumer/compose.py'),
                        str(self.payload)], check=True, cwd=self.root)

    def test_chezmoi_example_has_explicit_override_no_deep_merge(self):
        # Runtime producer/consumer tests require no chezmoi. Optional extraction-time
        # rendering of this literal example is recorded separately in validation.md.
        example = (ROOT / 'fixtures/consumer/chezmoi.json.tmpl').read_text()
        self.assertIn('.mappings.stylus.dark', example)
        self.assertIn('"accentColor" "blue"', example)
        self.assertNotIn('merge', example.lower())

    def test_offline_audit_hook_blocks_network(self):
        program = ("import importlib.util, socket, sys; "
                   f"s=importlib.util.spec_from_file_location('p', {str(ROOT / 'tools/build.py')!r}); "
                   "p=importlib.util.module_from_spec(s); s.loader.exec_module(p); "
                   "sys.addaudithook(p.deny_network); socket.create_connection(('127.0.0.1', 9))")
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('network access denied', result.stderr)

    def test_refresh_is_explicit_and_mocked(self):
        vendor = ROOT / 'applications/stylus/vendor'
        lock, inputs = stylus.vendor_inputs(vendor)
        urls = {value['url']: inputs[name] for name, value in lock['files'].items()}
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            with patch.object(stylus, 'download', side_effect=urls.__getitem__) as download:
                stylus.update(Path(directory), lock['standard_commit'], lock['files']['export.json']['url'])
            self.assertEqual(download.call_count, 7)
            _, refreshed = stylus.vendor_inputs(Path(directory))
            self.assertEqual(inputs, refreshed)

    def test_rejects_invalid_identity_and_output_overlap(self):
        for version, revision in (('../bad', REVISION), ('01.0.0', REVISION), ('0.1.0', 'main')):
            with self.assertRaises(ValueError):
                producer.build(self.root / 'invalid', self.root / 'invalid-cache', version, revision)
        with self.assertRaisesRegex(ValueError, 'absent or empty'):
            producer.build(self.output, self.root / 'cache', '0.1.0-dev', REVISION)
        with self.assertRaisesRegex(ValueError, 'outside source inputs'):
            producer.build(ROOT / 'palette/output', self.root / 'cache', '0.1.0-dev', REVISION)
        with self.assertRaisesRegex(ValueError, 'separate'):
            producer.build(self.root / 'nested', self.root / 'nested/cache', '0.1.0-dev', REVISION)

    def test_archive_corruption_and_unsafe_members_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            root = Path(directory)
            archive = root / self.archive.name
            sums = root / 'SHA256SUMS'
            archive.write_bytes(self.archive.read_bytes()[:-10])
            sums.write_bytes((self.output / 'SHA256SUMS').read_bytes())
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                verifier.verify(archive, sums)
            for name, data, mode in (('../escape', b'', 0o100644),
                                     ('symlink', b'../escape', 0o120777),
                                     ('palette/dark.json', b'{}', 0o100644),
                                     ('extra.json', b'{}', 0o100644)):
                with zipfile.ZipFile(self.archive) as original, zipfile.ZipFile(archive, 'w') as changed:
                    for entry in original.infolist():
                        if entry.filename != name:
                            changed.writestr(entry, original.read(entry.filename))
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = mode << 16
                    changed.writestr(info, data)
                sums.write_text(f'{stylus.digest(archive.read_bytes())}  {archive.name}\n')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    verifier.verify(archive, sums)

    def assert_rehashed_payload_rejected(self, mutate, message):
        # Recompute BOTH native/report/manifest hashes and the external checksum.
        # A rejection must exercise the contract, never stale integrity metadata.
        with zipfile.ZipFile(self.archive) as original:
            entries = original.infolist()
            payload = {entry.filename: original.read(entry.filename) for entry in entries}
        documents = {name: json.loads(data) for name, data in payload.items() if name.endswith('.json')}
        mutate(documents)
        for name, value in documents.items():
            payload[name] = stylus.json_bytes(value)
        report = documents['reports/stylus-build.json']
        if isinstance(report.get('artifacts'), dict):
            for name in report['artifacts']:
                native_path = f'themes/stylus/{name}'
                if native_path in payload:
                    report['artifacts'][name] = stylus.digest(payload[native_path])
        payload['reports/stylus-build.json'] = stylus.json_bytes(report)
        manifest = documents['manifest.json']
        manifest['artifacts'] = {name: stylus.digest(data) for name, data in payload.items()
                                 if name != 'manifest.json'}
        payload['manifest.json'] = stylus.json_bytes(manifest)
        with tempfile.TemporaryDirectory(dir=self.root) as directory:
            archive = Path(directory) / self.archive.name
            sums = Path(directory) / 'SHA256SUMS'
            with zipfile.ZipFile(archive, 'w') as changed:
                for entry in entries:
                    changed.writestr(entry, payload[entry.filename])
            sums.write_text(f'{stylus.digest(archive.read_bytes())}  {archive.name}\n')
            with self.assertRaisesRegex(ValueError, message):
                verifier.verify(archive, sums)

    def test_rehashed_consistent_invalid_palettes_rejected(self):
        palette = stylus.load_json(self.payload / 'palette/dark.json')
        for bad in ({}, [], {**palette, 'extra': '#ffffff'}, {**palette, 'base': 123},
                    {**palette, 'base': '#ABCDEF'}, {**palette, 'base': 'reset'}):
            def mutate(documents):
                documents['palette/dark.json'] = bad
                documents['data/consumer.json']['palettes']['dark'] = bad
            with self.subTest(bad=bad):
                self.assert_rehashed_payload_rejected(mutate, 'palette:')

    def test_rehashed_consistent_invalid_mapping_shapes_and_defaults_rejected(self):
        mutations = [
            (lambda m: m.update(palette={}), 'resolved palette:'),
            (lambda m: m['palette'].update(text=True), 'resolved palette:'),
            (lambda m: m.update(flavor='latte'), 'Incorrect variant flavor'),
            (lambda m: m['usercssVariables'].update(lightFlavor='frappe'), 'flavor defaults'),
            (lambda m: m['usercssVariables'].update(accentColor='invalid'), 'accent default'),
            (lambda m: m['usercssVariables'].update(extra='ignored'), 'Stylus variables:'),
            (lambda m: m['settings'].update(updateInterval=False), 'global update policy'),
        ]
        for change, message in mutations:
            def mutate(documents):
                mapping = documents['mappings/stylus/dark.json']
                change(mapping)
                documents['data/consumer.json']['mappings']['stylus']['dark'] = mapping
                documents['reports/stylus-build.json']['palettes']['dark'] = mapping['palette']
            with self.subTest(message=message):
                self.assert_rehashed_payload_rejected(mutate, message)

    def test_rehashed_consumer_variant_and_release_types_rejected(self):
        for path, value, message in [
            (('schemaVersion',), True, 'consumer schema'),
            (('palettes', 'extra'), {}, 'palette variants'),
            (('mappings', 'stylus', 'extra'), {}, 'mapping variants'),
            (('release', 'version'), '0.1.0-01', 'semantic version'),
            (('release', 'sourceRevision'), 123, 'source revision'),
            (('release', 'archiveSha256'), 'f' * 64, 'release: unexpected fields'),
        ]:
            def mutate(documents):
                target = documents['data/consumer.json']
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                if path[0] == 'release':
                    documents['manifest.json']['release'] = documents['data/consumer.json']['release']
            with self.subTest(path=path):
                self.assert_rehashed_payload_rejected(mutate, message)

    def test_rehashed_invalid_manifest_metadata_rejected(self):
        mutations = [
            (lambda m: m.update(schemaVersion=True), 'manifest schema'),
            (lambda m: m['applications']['stylus'].update(styles=0), 'manifest style count'),
            (lambda m: m['applications']['stylus'].update(format='other'), 'compatibility metadata'),
            (lambda m: m['applications']['stylus'].update(compatibility='untested'), 'compatibility metadata'),
            (lambda m: m['applications']['stylus'].update(nativeNames=[]), 'manifest native names'),
            (lambda m: m['applications']['stylus']['flavors'].update(dark='latte'), 'manifest flavors'),
            (lambda m: m.update(buildInputs={}), 'manifest build inputs:'),
            (lambda m: m['buildInputs'].update({'tools/build.py': 'bad'}), 'expected SHA-256'),
        ]
        for change, message in mutations:
            with self.subTest(message=message):
                self.assert_rehashed_payload_rejected(lambda d: change(d['manifest.json']), message)

    def test_rehashed_empty_native_and_missing_report_artifacts_rejected(self):
        def empty_both(documents):
            documents['themes/stylus/import.json'] = []
            documents['reports/stylus-build.json']['artifacts'] = {}
        self.assert_rehashed_payload_rejected(empty_both, 'report artifacts:')
        self.assert_rehashed_payload_rejected(
            lambda d: d.update({'themes/stylus/import.json': []}), 'Native names/count')
        for missing in ('import.json', 'lib.less'):
            with self.subTest(missing=missing):
                self.assert_rehashed_payload_rejected(
                    lambda d: d['reports/stylus-build.json']['artifacts'].pop(missing), 'report artifacts:')

    def test_rehashed_native_names_settings_and_defaults_rejected(self):
        mutations = [
            (lambda records: records[1].update(name='Renamed'), 'Native names/count'),
            (lambda records: records[0]['settings'].update(updateInterval=24), 'global update policy'),
            (lambda records: records.pop(0), 'Native settings/count/defaults'),
            (lambda records: records[1]['usercssData']['vars']['accentColor'].update(value='blue'),
             'Native accentColor: incorrect saved default'),
            (lambda records: records[1]['usercssData']['vars']['lightFlavor'].update(default='frappe'),
             'Native lightFlavor: incorrect flavor default'),
        ]
        for change, message in mutations:
            with self.subTest(message=message):
                self.assert_rehashed_payload_rejected(lambda d: change(d['themes/stylus/import.json']), message)
        # Even mutually consistent native/consumer/report defaults must satisfy the contract.
        def invalid_everywhere(documents):
            for variant in ('dark', 'light'):
                documents[f'mappings/stylus/{variant}.json']['usercssVariables']['accentColor'] = 'invalid'
                documents['data/consumer.json']['mappings']['stylus'][variant]['usercssVariables']['accentColor'] = 'invalid'
            documents['reports/stylus-build.json']['summary']['accents'] = ['invalid']
            for record in documents['themes/stylus/import.json']:
                if 'sourceCode' in record:
                    record['usercssData']['vars']['accentColor']['value'] = 'invalid'
        self.assert_rehashed_payload_rejected(invalid_everywhere, 'Invalid Stylus accent default')

    def test_shared_contract_roles_and_schema_agree(self):
        contract = verifier.contract
        schema = stylus.load_json(ROOT / 'schemas/consumer.schema.json')
        self.assertEqual(set(contract.PALETTE_ROLES),
                         set(stylus.load_json(ROOT / 'schemas/palette.schema.json')['required']))
        self.assertEqual(set(contract.BROWSER_ROLES),
                         set(schema['$defs']['stylusMapping']['properties']['palette']['required']))
        self.assertEqual(set(contract.ACCENTS),
                         set(schema['$defs']['stylusMapping']['properties']['usercssVariables']['properties']['accentColor']['enum']))
        self.assertEqual(schema['properties']['release']['properties']['version']['pattern'],
                         '^' + contract.VERSION_PATTERN + '$')

    def test_two_isolated_checkouts_homes_caches_and_archives(self):
        archives = []
        for index in range(2):
            root = self.root / f'isolation {index}'
            checkout = root / 'checkout with spaces'
            for name in ('palette', 'applications', 'tools', 'schemas', 'licenses'):
                shutil.copytree(ROOT / name, checkout / name,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            home = root / 'empty home'
            home.mkdir()
            env = {'HOME': str(home), 'USERPROFILE': str(home),
                   'XDG_CONFIG_HOME': str(root / 'config'), 'XDG_DATA_HOME': str(root / 'data'),
                   'XDG_CACHE_HOME': str(root / 'xdg cache'),
                   'PATH': str(Path(sys.executable).parent), 'SYSTEMROOT': os.environ.get('SYSTEMROOT', '')}
            output = root / 'output with spaces'
            cache = root / 'cache with spaces'
            cache.mkdir()
            # Deliberately poison diagnostics: fitting must never read them as inputs.
            (cache / 'stylus').mkdir()
            (cache / 'stylus/filters-v1.json').write_text('corrupt cache')
            subprocess.run([sys.executable, '-I', '-B', str(checkout / 'tools/build.py'),
                            '--output', str(output), '--cache', str(cache),
                            '--version', '0.1.0-dev', '--source-revision', REVISION],
                           check=True, cwd=home, env=env)
            verifier.verify(output / self.archive.name, output / 'SHA256SUMS')
            archives.append((output / self.archive.name).read_bytes())
            self.assertEqual(list(home.iterdir()), [])
            for name in ('config', 'data', 'xdg cache'):
                self.assertFalse((root / name).exists())
        self.assertEqual(archives[0], archives[1])
        self.assertEqual(archives[0], self.archive.read_bytes())


if __name__ == '__main__':
    unittest.main()
