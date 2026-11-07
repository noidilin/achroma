"""CI-only clean-source identity, isolated checks, and immutable release handoff."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract
import verify

ROOT = Path(__file__).resolve().parents[1]


def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def identity(tag='', root=ROOT):
    if git('status', '--porcelain', '--untracked-files=all', root=root):
        raise ValueError('CI requires committed, clean source (ignored scratch files are allowed)')
    revision = git('rev-parse', 'HEAD', root=root)
    version = tag[1:] if tag.startswith('v') else '0.1.0-dev'
    contract.validate_release({'version': version, 'sourceRevision': revision})
    if tag:
        if tag != 'v' + version:
            raise ValueError('Release tags must be v<semantic-version>')
        if git('rev-parse', '--verify', f'refs/tags/{tag}^{{commit}}', root=root) != revision:
            raise ValueError('Checked-out commit does not match release tag')
        notes = f'docs/releases/{version}.md'
        git('ls-files', '--error-unmatch', '--', notes, root=root)
        if not (root / notes).read_text(encoding='utf-8').strip():
            raise ValueError('Committed release notes must not be empty')
    return {'version': version, 'sourceRevision': revision}


def require_network_namespace():
    # A new Linux network namespace has only a down loopback interface. This
    # checks the whole process boundary, not Python/Node monkeypatch coverage.
    if sys.platform != 'linux' or {name for _, name in socket.if_nameindex()} != {'lo'}:
        raise ValueError('CI checks require a fresh Linux network namespace (only loopback)')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle(output, destination, release, tag, root=ROOT):
    archive = output / f'achroma-{release["version"]}.zip'
    manifest = verify.verify(archive, output / 'SHA256SUMS')
    if manifest['release'] != release:
        raise ValueError('Verified archive identity differs from checked-out source')
    for name, expected in manifest['buildInputs'].items():
        if digest(root / name) != expected:
            raise ValueError(f'Archive input differs from checked-out source: {name}')
    destination.mkdir()  # Never reuse a mutable handoff directory.
    for path in (archive, output / 'SHA256SUMS'):
        shutil.copyfile(path, destination / path.name)
    (destination / 'SOURCE.json').write_text(
        json.dumps({'release': release, 'tag': tag}, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    if tag:
        shutil.copyfile(root / f'docs/releases/{release["version"]}.md', destination / 'RELEASE_NOTES.md')
    checksums = ''.join(f'{digest(path)}  {path.name}\n' for path in sorted(destination.iterdir()))
    transfer = destination / 'TRANSFER.sha256'
    transfer.write_text(checksums, encoding='utf-8')
    return digest(transfer)


def check(tag):
    require_network_namespace()
    release = identity(tag)
    python = [sys.executable, '-I', '-B']
    output = ROOT / '.work/ci-candidate'
    cache = ROOT / '.work/ci-cache'
    args = ['--version', release['version'], '--source-revision', release['sourceRevision']]
    subprocess.run(python + [str(ROOT / 'tools/check.py'), '--output', str(output),
                            '--cache', str(cache), *args], cwd=ROOT, check=True)
    # Also reproduce the *actual* release identity, not just the fixture version
    # used by the contract suite, in an independent checkout/HOME/XDG/cache.
    with tempfile.TemporaryDirectory(dir=ROOT / '.work', prefix='ci-isolation-') as temporary:
        isolated = Path(temporary)
        checkout = isolated / 'checkout with spaces'
        for name in ('palette', 'applications', 'tools', 'schemas', 'licenses'):
            shutil.copytree(ROOT / name, checkout / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        home = isolated / 'empty home'
        home.mkdir()
        env = {**os.environ, 'HOME': str(home), 'USERPROFILE': str(home),
               'XDG_CONFIG_HOME': str(isolated / 'config'), 'XDG_DATA_HOME': str(isolated / 'data'),
               'XDG_CACHE_HOME': str(isolated / 'xdg cache'), 'TMPDIR': str(isolated)}
        second = isolated / 'output'
        subprocess.run(python + [str(checkout / 'tools/build.py'), '--output', str(second),
                                '--cache', str(isolated / 'cache'), *args],
                       cwd=home, env=env, check=True)
        verify.verify(second / f'achroma-{release["version"]}.zip', second / 'SHA256SUMS')
        for name in ('SHA256SUMS', f'achroma-{release["version"]}.zip'):
            if (output / name).read_bytes() != (second / name).read_bytes():
                raise ValueError(f'Isolated build is not reproducible: {name}')
    if identity(tag) != release:
        raise ValueError('Source identity changed during checks')
    transfer_digest = bundle(output, ROOT / '.work/ci-bundle', release, tag)
    return release, transfer_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('identity', 'check'))
    parser.add_argument('--tag', default='')
    args = parser.parse_args()
    try:
        if args.mode == 'identity':
            release, transfer = identity(args.tag), None
        else:
            release, transfer = check(args.tag)
        values = {'version': release['version'], 'revision': release['sourceRevision']}
        if transfer:
            values['transfer-sha256'] = transfer
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
                for name, value in values.items():
                    stream.write(f'{name}={value}\n')
        print(json.dumps(values, sort_keys=True))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'achroma-ci: {error}\n')


if __name__ == '__main__':
    main()
