"""Offline optional UserCSS renderer and explicit upstream snapshot/check commands."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'applications/stylus/complement'
URL = 'https://userstyles.world/api/style/25419.user.css'
ARTIFACT = contract.COMPLEMENT_ARTIFACT
PREFIX = '--achroma-complement-'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata(data):
    source = data.decode('utf-8')
    header = re.search(r'/\*\s*==UserStyle==(.*?)==/UserStyle==\s*\*/', source, re.S)
    if not header:
        raise ValueError('Missing upstream UserStyle metadata')
    fields = dict(re.findall(r'^\s*@(\w+)\s+([^\n]+)', header[1], re.M))
    if fields.get('name', '').strip() != 'achroma complement' or fields.get('license', '').strip() != 'MIT':
        raise ValueError('Upstream identity/license changed; manual review required')
    version = fields.get('version', '').strip()
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', version):
        raise ValueError('Unexpected upstream version')
    return version


def upstream_inputs(directory=SOURCE):
    lock = json.loads((directory / 'upstream.lock.json').read_text(encoding='utf-8'))
    contract.object_keys(lock, ('schema', 'url', 'version', 'license', 'sha256'), 'complement upstream lock')
    contract.require(type(lock['schema']) is int and lock['schema'] == 1 and lock['url'] == URL
                     and lock['license'] == 'MIT', 'Unexpected complement provenance')
    contract.digest(lock['sha256'], 'complement source checksum')
    data = (directory / 'upstream.user.css').read_bytes()
    contract.require(digest(data) == lock['sha256'], 'Complement upstream checksum mismatch')
    contract.require(metadata(data) == lock['version'], 'Complement upstream version mismatch')
    return lock, data


def render(palettes, version, directory=SOURCE):
    contract.validate_release({'version': version, 'sourceRevision': '0' * 40})
    contract.object_keys(palettes, ('dark', 'light'), 'complement palette variants')
    for palette in palettes.values():
        contract.validate_palette(palette)
    lock, _ = upstream_inputs(directory)
    template = (directory / 'style.css.tmpl').read_text(encoding='utf-8')
    roles = set(re.findall(r'var\(--achroma-complement-([a-zA-Z0-9]+)\)', template))
    contract.require(bool(roles) and roles <= set(contract.PALETTE_ROLES), 'Unknown complement palette role')

    def declarations(variant, indent):
        return '\n'.join(f'{indent}{PREFIX}{role}: {palettes[variant][role]};' for role in sorted(roles))

    replacements = {'{{VERSION}}': version, '{{SOURCE_SHA256}}': lock['sha256'],
                    '{{LIGHT_PALETTE}}': declarations('light', '    '),
                    '{{DARK_PALETTE}}': declarations('dark', '      ')}
    for key, value in replacements.items():
        contract.require(template.count(key) == 1, f'Expected one complement template marker: {key}')
        template = template.replace(key, value)
    validate(template, palettes, version)
    return template.encode('utf-8')


def validate(source, palettes, version):
    """Structural archive checks; real CSS parsing and visual acceptance are separate."""
    contract.text(source, 'complement UserCSS')
    for key, expected in (('name', 'Achroma complement'), ('version', version),
                          ('namespace', 'https://github.com/noidilin/achroma/complement'),
                          ('license', 'MIT')):
        values = re.findall(r'^@' + key + r'\s+([^\n]+)', source, re.M)
        contract.require(values == [expected], f'Unexpected complement {key}')
    contract.require(not re.search(r'@import\b|^\s*@updateURL\b|url\(', source, re.M | re.I),
                     'Complement must be self-contained with no update URL')
    contract.require('{{' not in source, 'Unresolved complement template marker')
    roots = re.findall(r':root\s*\{([^{}]*)\}', source)
    contract.require(len(roots) == 2, 'Expected light and dark complement palettes')
    roles = set(re.findall(r'var\(--achroma-complement-([a-zA-Z0-9]+)\)', source))
    contract.require(bool(roles) and roles <= set(contract.PALETTE_ROLES), 'Unknown complement palette role')
    for variant, block in zip(('light', 'dark'), roots):
        declarations = re.findall(r'(--[a-zA-Z0-9-]+):\s*(#[0-9a-f]{6});', block)
        expected = [(PREFIX + role, palettes[variant][role]) for role in sorted(roles)]
        contract.require(declarations == expected, 'Complement palette differs from canonical palette')
        residue = re.sub(r'--[a-zA-Z0-9-]+:\s*#[0-9a-f]{6};', '', block)
        contract.require(not residue.strip(), 'Unexpected complement palette declaration')
    contract.require(re.search(r'@media\s*\(prefers-color-scheme: dark\)\s*\{\s*:root', source),
                     'Missing dark complement media condition')


def download():
    request = urllib.request.Request(URL, headers={'User-Agent': 'achroma-complement-updater'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def check_upstream(directory=SOURCE):
    lock, previous = upstream_inputs(directory)
    current = download()
    # Byte comparison catches edits even when the upstream version is unchanged.
    changed = current != previous
    print(json.dumps({'changed': changed, 'url': URL, 'pinnedVersion': lock['version'],
                      'pinnedSha256': lock['sha256'], 'downloadedSha256': digest(current)}, indent=2))
    return changed


def snapshot(directory):
    data = download()
    version = metadata(data)  # Validate identity/license before writing anything.
    directory.mkdir(parents=True)  # Never overwrite a reviewed snapshot or adapted template.
    (directory / 'upstream.user.css').write_bytes(data)
    lock = {'schema': 1, 'url': URL, 'version': version, 'license': 'MIT', 'sha256': digest(data)}
    (directory / 'upstream.lock.json').write_text(json.dumps(lock, indent=2) + '\n', encoding='utf-8')
    print('Staged upstream source only; manually review and port changes to style.css.tmpl.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check-upstream', help='Network check; exit 1 if source bytes changed; no writes')
    stage = commands.add_parser('snapshot-upstream', help='Download original into a NEW scratch directory')
    stage.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'check-upstream':
            changed = check_upstream()
            if changed:
                print('Review the upstream change; do not overwrite the adapted style.', file=sys.stderr)
                return 1
        else:
            snapshot(args.output)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f'achroma-complement: {error}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
