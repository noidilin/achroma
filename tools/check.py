"""Local CI contract. Prepare locked npm dependencies separately before running."""

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--source-revision', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    python = [sys.executable, '-I', '-B']

    def run(command):
        subprocess.run(command, cwd=ROOT, check=True)

    for directory in ('tests/stylus', 'tests'):
        run(python + ['-m', 'unittest', 'discover', '-s', directory, '-v'])
    run(python + [str(ROOT / 'tools/build.py'), '--output', str(output),
                  '--cache', str(args.cache.resolve()), '--version', args.version,
                  '--source-revision', args.source_revision])
    run(python + [str(ROOT / 'tools/verify.py'), str(output / f'achroma-{args.version}.zip'),
                  str(output / 'SHA256SUMS')])
    run(['node', str(ROOT / 'tests/stylus/check.mjs'),
         str(output / 'payload/themes/stylus/import.json'),
         str(output / 'payload/themes/stylus/lib.less')])
    run(['node', str(ROOT / 'tests/stylus/check-complement.mjs'),
         str(output / 'payload/themes/stylus/achroma-complement.user.css'),
         str(output / 'payload/palette/light.json'), str(output / 'payload/palette/dark.json')])
    run(python + [str(ROOT / 'fixtures/consumer/compose.py'), str(output / 'payload')])


if __name__ == '__main__':
    main()
