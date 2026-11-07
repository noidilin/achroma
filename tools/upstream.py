"""Scheduled snapshot proposals. Only `prepare` downloads; only `publish` writes remotely."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'applications/stylus'))
import build as stylus

VENDOR = Path('applications/stylus/vendor')
NAMES = {'export.json', 'std.less', 'LICENSE', *stylus.CSS_URLS, 'upstream.lock.json'}
EXPORT_URL = 'https://github.com/catppuccin/userstyles/releases/download/all-userstyles-export/import.json'
BRANCH = 'automation/catppuccin-refresh'
MESSAGE = 'chore: refresh Catppuccin snapshots [achroma-upstream-v1]'
SHA = re.compile(r'[0-9a-f]{40}\Z')


def revision(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError('Expected a full lowercase commit SHA')
    return value


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def api(method, endpoint, data=None, *, missing=False):
    # No shell, jq, or expression evaluation of upstream/API data.
    command = ['gh', 'api', '--method', method, endpoint]
    if data is not None:
        command += ['--input', '-']
    result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                            text=True, capture_output=True)
    if result.returncode:
        if missing and '(HTTP 404)' in result.stderr:
            return None
        raise RuntimeError(f'GitHub API {method} {endpoint} failed: {result.stderr}')
    return json.loads(result.stdout) if result.stdout.strip() else None


def read_candidate(directory):
    if directory.is_symlink() or {p.name for p in directory.iterdir()} != NAMES | {'proposal.json'}:
        raise ValueError('Unexpected proposal file set')
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise ValueError('Proposal must contain only regular files')
    report = json.loads((directory / 'proposal.json').read_text())
    if set(report) != {'base', 'standard_commit', 'checks'}:
        raise ValueError('Unexpected proposal metadata')
    revision(report['base'])
    commit = revision(report['standard_commit'])
    if set(report['checks']) != {'build', 'verify', 'compile', 'full_ci'} or any(
        type(value) is not int or not 0 <= value <= 255 for value in report['checks'].values()
    ):
        raise ValueError('Invalid validation results')
    lock, inputs = stylus.vendor_inputs(directory)
    if lock['standard_commit'] != commit:
        raise ValueError('Proposal revision differs from lock')
    base = f'https://raw.githubusercontent.com/catppuccin/userstyles/{commit}'
    urls = {'export.json': EXPORT_URL, 'std.less': f'{base}/lib/std/v1.less',
            'LICENSE': f'{base}/LICENSE', **stylus.CSS_URLS}
    if any(lock['files'][name]['url'] != url for name, url in urls.items()):
        raise ValueError('Unexpected snapshot provenance URL')
    if inputs['LICENSE'] != (ROOT / VENDOR / 'LICENSE').read_bytes():
        raise ValueError('Upstream LICENSE changed: manual license/provenance review required')
    return report, {name: (directory / name).read_bytes() for name in sorted(NAMES)}


def prepare(directory):
    base = revision(git('rev-parse', 'HEAD'))
    # Resolve the official default branch explicitly; never infer export/CSS revisions from it.
    upstream = json.loads(stylus.download('https://api.github.com/repos/catppuccin/userstyles/commits/HEAD'))
    commit = revision(upstream['sha'])
    directory.mkdir(parents=True)  # Refuse reuse of a stale handoff.
    stylus.update(directory, commit, EXPORT_URL)
    if (directory / 'LICENSE').read_bytes() != (ROOT / VENDOR / 'LICENSE').read_bytes():
        raise ValueError('Upstream LICENSE changed: manual license/provenance review required')
    changed = any((directory / name).read_bytes() != (ROOT / VENDOR / name).read_bytes()
                  for name in NAMES)
    if not changed:
        shutil.rmtree(directory)
    else:
        # Results are filled by the offline validation phase, before artifact upload.
        report = {'base': base, 'standard_commit': commit,
                  'checks': dict.fromkeys(('build', 'verify', 'compile', 'full_ci'), 125)}
        (directory / 'proposal.json').write_bytes(stylus.json_bytes(report))
        for name in NAMES:
            shutil.copyfile(directory / name, ROOT / VENDOR / name)
        git('add', '--', str(VENDOR))
        git('-c', 'user.name=Achroma refresh validation', '-c',
            'user.email=achroma-validation@users.noreply.github.com', 'commit', '-m', MESSAGE)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write(f'changed={str(changed).lower()}\n')
    return changed


def validate(directory):
    # Called inside a read-only-token, network-isolated job. Upstream bytes are data only.
    sys.path.insert(0, str(ROOT / 'tools'))
    import ci
    ci.require_network_namespace()
    report, _ = read_candidate(directory)
    python = [sys.executable, '-I', '-B']
    output = ROOT / '.work/upstream-build'
    commands = {
        'build': python + ['tools/build.py', '--output', str(output), '--cache',
                           str(ROOT / '.work/upstream-cache'), '--version', '0.1.0-dev',
                           '--source-revision', git('rev-parse', 'HEAD')],
        'verify': python + ['tools/verify.py', str(output / 'achroma-0.1.0-dev.zip'),
                            str(output / 'SHA256SUMS')],
        'compile': ['node', 'tests/stylus/check.mjs', str(output / 'payload/themes/stylus/import.json'),
                    str(output / 'payload/themes/stylus/lib.less')],
        'full_ci': python + ['tools/ci.py', 'check'],
    }
    for name, command in commands.items():
        # A failed baseline is evidence, not permission to bless fixtures. Draft PRs retain it.
        code = subprocess.run(command, cwd=ROOT).returncode
        report['checks'][name] = code if 0 <= code <= 255 else 1
    (directory / 'proposal.json').write_bytes(stylus.json_bytes(report))
    print(json.dumps(report, indent=2))


def proposal_body(report, run_url):
    checks = '\n'.join(f'- {name}: exit {code}' for name, code in report['checks'].items())
    return (f'Automated **draft proposal**, not merge or release approval.\n\n'
            f'Standard library revision: `{report["standard_commit"]}`\n'
            f'Base revision: `{report["base"]}`\n\n'
            'Export and syntax CSS are independently downloaded and checksummed; they do not '
            'claim the standard-library revision. See the lock diff for exact bytes/URLs.\n\n'
            f'Validation on a local synthetic candidate commit: [run/logs]({run_url}).\n{checks}\n\n'
            'These are explicit refresh-job checks, not PR CI. GITHUB_TOKEN does not trigger '
            'ordinary push/PR CI. Required `check` remains unsatisfied until a maintainer '
            'closes/reopens this PR using their own identity (or pushes a reviewed change). '
            'Require green checks on the exact final candidate before merge.\n\n'
            'Review snapshots, independent CSS notices/provenance, exclusions and all native '
            'output changes. LICENSE bytes are unchanged; this does not establish complete '
            'license compliance. Follow docs/upstream-refresh.md for intentional baseline '
            'changes and browser acceptance. No fixtures, palettes, filter locks or notices '
            'were automatically updated. No automatic merge or publication.\n')


def publish(directory, repository, run_url):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    if not re.fullmatch(r'https://github.com/' + re.escape(repository) + r'/actions/runs/[0-9]+', run_url):
        raise ValueError('Invalid run URL')
    report, files = read_candidate(directory)
    base = report['base']
    if revision(git('rev-parse', 'HEAD')) != base:
        raise ValueError('Publisher checkout differs from proposal base')
    if all(data == (ROOT / VENDOR / name).read_bytes() for name, data in files.items()):
        return  # No remote mutation, PR, or commit on no-op.
    prefix = f'repos/{repository}'
    if api('GET', f'{prefix}/git/ref/heads/main')['object']['sha'] != base:
        raise ValueError('Main moved; rerun refresh rather than publishing stale data')
    pulls = api('GET', f'{prefix}/pulls?state=all&head={repository.split("/")[0]}:{BRANCH}&per_page=100')
    opened = [pr for pr in pulls if pr['state'] == 'open']
    if len(opened) > 1 or any(pr['base']['ref'] != 'main' for pr in opened):
        raise ValueError('Unexpected refresh PR state')
    if not opened and any(not pr.get('merged_at') for pr in pulls):
        raise ValueError('Refresh PR was closed without merge; operator must reopen it to resume')
    ref = api('GET', f'{prefix}/git/ref/heads/{BRANCH}', missing=True)
    old = None
    if ref:
        old = revision(ref['object']['sha'])
        head = api('GET', f'{prefix}/commits/{old}')
        if head['commit']['message'] != MESSAGE or (head.get('author') or {}).get('login') != 'github-actions[bot]':
            raise ValueError('Refresh branch has human/unrecognized changes; refusing to overwrite')
        comparison = api('GET', f'{prefix}/compare/{base}...{old}')
        if any(item['filename'] not in {str(VENDOR / name) for name in NAMES}
               or item['status'] not in ('modified', 'added') for item in comparison['files']):
            raise ValueError('Refresh branch contains changes outside the snapshot allowlist')
    tree = api('POST', f'{prefix}/git/trees', {
        'base_tree': git('rev-parse', 'HEAD^{tree}'),
        'tree': [{'path': str(VENDOR / name), 'mode': '100644', 'type': 'blob',
                  'content': data.decode('utf-8')} for name, data in files.items()],
    })['sha']
    if not ref or head['commit']['tree']['sha'] != tree:
        commit = api('POST', f'{prefix}/git/commits',
                     {'message': MESSAGE, 'tree': tree, 'parents': [base]})['sha']
        # Workflow concurrency serializes all scheduled/manual writers. Refuse observed edits.
        current = api('GET', f'{prefix}/git/ref/heads/{BRANCH}', missing=True)
        if (current['object']['sha'] if current else None) != old:
            raise ValueError('Refresh branch moved during publication; refusing to overwrite')
        if ref:
            api('PATCH', f'{prefix}/git/refs/heads/{BRANCH}', {'sha': commit, 'force': True})
        else:
            api('POST', f'{prefix}/git/refs', {'ref': f'refs/heads/{BRANCH}', 'sha': commit})
    body = proposal_body(report, run_url)
    if opened:
        # Do not reset review status or enable auto-merge; update evidence only.
        api('PATCH', f'{prefix}/pulls/{opened[0]["number"]}', {'body': body})
    else:
        api('POST', f'{prefix}/pulls', {'title': 'chore: refresh Catppuccin upstream snapshots',
            'head': BRANCH, 'base': 'main', 'draft': True, 'body': body})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'validate', 'publish'))
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == 'prepare':
            prepare(args.candidate)
        elif args.mode == 'validate':
            validate(args.candidate)
        else:
            publish(args.candidate, os.environ['GH_REPO'], os.environ['REFRESH_RUN_URL'])
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'achroma-upstream: {error}\n')


if __name__ == '__main__':
    main()
