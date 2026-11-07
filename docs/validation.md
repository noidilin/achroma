# Extraction validation checkpoint

This records the **completed independent-review remediation validation**, not
completion of the earlier timed-out run. Local checkout: `achroma-source`, branch `feat/standalone-stylus`,
uncommitted and unstaged. Baseline HEAD remains
`41572a8510f6ce8f567b12371d91016eec1a90f6`, matching the inspected remote baseline.
SSH cloning failed; the supervisor-approved HTTPS transport fallback cloned the
same public repository and restored SSH origin. No global Git/SSH settings changed.

## Completed checks

Python **3.13.13**, Node **22.17.1**, on macOS. Preparation (prior run):
`npm ci --prefix tests/stylus --ignore-scripts --no-audit --no-fund` succeeded.
The original source's 22 tests and compiler baseline had also passed before the
timeout; their scratch logs are retained separately from fresh retry evidence.

Latest command, from this checkout, with TMPDIR inside `.work/review-fix-tmp`
and the above Python/Node selected explicitly:

```sh
python3 -B tools/check.py --output .work/review-fixed --cache .work/review-fixed-cache \
  --version 0.1.0-dev --source-revision 41572a8510f6ce8f567b12371d91016eec1a90f6
```

Result (`.work/review-fix-full.log`; focused contract run: `.work/review-fix-focused.log`):

- Relocated Stylus suite: **22 passed**. The two old consumer-specific XDG/wrapper
  tests now verify required explicit CLI paths and standalone path isolation;
  they no longer require chezmoi/mise/platform wrappers.
- Producer contract suite: **22 passed** (seven new test methods with multiple
  negative subcases), including exact consumer fixture/schema fields,
  aggregate/individual equality, external-only checksum metadata, real palette,
  source fixture hashes, licenses in payload, frozen legacy hash, offline network
  rejection, mocked explicit refresh, archive corruption/member rejection, plain
  Python overrides, and two isolated source/home/cache builds with spaces and
  poisoned diagnostic caches.
- New regressions recompute native/report/manifest hashes and external ZIP
  checksums before rejection. Cases include mutually consistent empty/invalid
  palettes, malformed resolved colors/defaults/variant keys, invalid release
  identities and manifest metadata, empty native export, missing report artifact
  entries, and mismatched native names/settings/defaults. These exercise contract
  validation rather than stale integrity hashes.
- Both isolated ZIP files and the local candidate are **byte-identical**.
- Archive verification: **15 payload artifacts**, no unsafe members or symlinks.
- Compilation: **132 UserCSS styles × 2 paths**, **310 document sections**, helper
  fixtures passed. The compiler rejects runtime network access.
- Plain Python consumer passed without chezmoi.

The optional chezmoi consumer template was also rendered using an empty scratch
source/config, scratch HOME/XDG paths, and `--override-data` containing the same
producer aggregate. Parsed output equalled
`{"lightFlavor":"latte","darkFlavor":"mocha","accentColor":"blue"}`.
This was an extraction-time consumer check, not a producer dependency.

## Fidelity and artifacts

Both 66-key palettes equal the rendered source and a separate mechanical parse of
`colors.yml` at dotfiles revision `530cad951a3f1e401774839f3c8a2853240341b1`.
Filters, browser mapping, vendor snapshots/lock/license, and npm lock remain
byte-identical to source. Native `cmp` checks against scratch baseline outputs
passed. There are **no palette, selector, exclusion, setting, or flavor changes**.
The native build report differs only in `fingerprint` because the builder was
relocated/adapted. Supplementary upstream MIT notices were collected with immutable
license-source provenance; original vendor bytes were not refreshed.

Latest artifacts live under ignored `.work/review-fixed/`:

| Artifact | SHA-256 |
| --- | --- |
| `achroma-0.1.0-dev.zip` | `0a1c0b12a81ea226d5b79b43f9ddb6a651df467df353d5ebfab93833ba064c7a` |
| `payload/themes/stylus/import.json` | `84cb4b1cfba2cb41076c8e2984cd254feded67b36a26b982e2e40db7ae7615b1` |
| `payload/themes/stylus/lib.less` | `8e0bd1e98e92c7560f175132838d58e2103065514997f281a8916e3b93274717` |
| frozen source `lib/lib.less` | `73f2609f5346c5bab0afa0bed0db4b1b9a7eff83b94d1321bdf18194acf21f22` |

Hashes identify this uncommitted local candidate, **not a published version**.
Input hashes in its manifest identify the actual producer inputs beyond HEAD.
Compared with the preceding `8842705f...` checkpoint, only `manifest.json` differs
inside the payload: all 15 hashed payload artifacts remain byte-identical. The
manifest now records 22 build inputs, including shared `tools/contract.py`, and
the aligned release-version schema/producer hashes. Native bytes still match the
original scratch baseline; frozen legacy bytes remain unchanged.

## Independent-review fixes

The reviewer reproduced two acceptance holes in the earlier verifier. Both are
now covered by explicit stdlib validators shared with the producer, not a general
JSON Schema engine:

1. Exact palette role sets, types and hex values; nested consumer and mapping
   keys/defaults; semantic release identity; and complete manifest application,
   native-name/count, build-input and artifact metadata are validated. Shared
   role/version definitions are regression-checked against declared schemas.
2. Report artifacts must contain exactly `import.json` and `lib.less`, with both
   hashes matching the manifest. The verifier parses native records and compares
   names/count, the global update setting, and effective saved variable defaults
   to report/manifest/mappings. Upstream's extra `subtext0` native accent option
   and original default metadata remain intact.

The first focused run exposed that preserved extra option; validation was fixed
to recognize it without changing any native bytes. The subsequent focused and
full runs both passed. Independent re-review accepted both fixes with no new
blockers for the bounded standalone pilot.

## Independent acceptance

The reviewer independently reran `python3 -I -B tools/check.py` with scratch
output/cache: all 44 Python tests and 132 styles × 2 paths / 310 document sections
passed, including archive verification and the consumer example. Both original
malformed-archive probes were rejected after recomputing checksums. All 22 input
hashes matched, and the candidate archive reproduced the SHA-256 above.
Reviewer evidence: `/tmp/achroma-rereview.GJfG9A/check.log` (local, disposable).
Approval covers this standalone pilot only, not deferred integration or publication.

## Boundaries and remaining work

Dotfiles HEAD/status were rechecked: only the original dirty herdr, Claude settings,
wallpapers, and untracked extraction plan remained. No edits were made there.
Achroma's legacy library and markdownlint tracked bytes are unchanged; no remote
Pages configuration was changed (remote settings were not independently re-audited).
No staged files, commits, pushes, publication, live installation, browser import,
or OS appearance changes occurred.

Caveat: the earlier npm preparation omitted an explicit `--cache`, so npm may have
used its default external cache/log location. This is not an audited guarantee of
all process writes staying inside the checkout; it did not install dependencies
into dotfiles. Future preparation should pass a checkout-local cache explicitly.

Independent review approved the bounded standalone pilot. Browser import/visual
tests, Windows/Linux execution, remotely executed pinned CI, tag-only publication,
and trusted release review are not completed. Installer, dotfiles snapshot/pin, rollback, and native
activation changes remain deferred. See the installation-before-activation and
cache-absent committed-pin rollback constraints in `consumption.md`.

## CI + first-release preparation checkpoint

The independent acceptance above remains the palette/Stylus baseline. This next
bounded phase adds workflows, CI-only identity/isolation/handoff helpers and nine
regressions; it does not change producer/native output code or approved fixtures.
It does **not** complete publication, Linux/remote execution, or browser acceptance.

Local validation used Python **3.13.13**, Node **22.17.1**, and checkout-local
`TMPDIR=.work/ci-phase-tmp`:

```sh
python3 -I -B tools/check.py --output .work/ci-phase-final --cache .work/ci-phase-final-cache \
  --version 0.1.0-dev --source-revision 41572a8510f6ce8f567b12371d91016eec1a90f6
actionlint .github/workflows/ci.yml .github/workflows/release.yml
bash -n tools/ci.sh
```

Results:

- **53 tests passed** (22 relocated, 22 approved contract, nine CI identity,
  clean-source, semantic tag/notes, namespace boundary, transfer integrity and
  static workflow-policy regressions). Full log: `.work/ci-phase-final.log`.
- **132 styles × 2 paths / 310 document sections**, archive verification and the
  plain Python consumer passed. Isolated fixture-version builds reproduce the
  approved ZIP hash `0a1c0b12a81ea226d5b79b43f9ddb6a651df467df353d5ebfab93833ba064c7a`.
  `cmp` against `.work/review-fixed/achroma-0.1.0-dev.zip` passed. The approved
  evidence directory is preserved. Native/frozen legacy bytes remain unchanged.
- Actionlint **1.7.12** and `bash -n` passed; static log:
  `.work/ci-preparation/actionlint.log` (empty on success). This is **not** remote
  GitHub Actions execution or proof of Linux namespace/runtime availability.
- `tools/ci.py identity` correctly refused this uncommitted tree; `tools/ci.py check`
  correctly refused macOS rather than bypassing Linux isolation. Expected exit
  status 1 logs: `.work/ci-preparation/{identity-refusal,namespace-refusal}.log`.
- All five action pins were verified from official repository tag refs using
  read-only `git ls-remote`; exact log and fetched official action input definitions
  are under `.work/ci-preparation/`. Sources/pins are documented in `release.md`.
- `git diff --check` passed; no staged files. Legacy `lib/lib.less` and tracked
  markdownlint settings match HEAD. Dotfiles remains at `530cad951a3f1e401774839f3c8a2853240341b1`
  with only the previously identified dirty/untracked paths; no dotfiles content
  was edited. No tags, commits, pushes, production workflows, remote settings,
  secrets, installations or live application state were used/changed.

Boundary caveat: the first focused CI-unittest invocation omitted `TMPDIR` and
used automatically cleaned system temporary directories for its synthetic test
files. Subsequent full validations used checkout-local scratch. No persistent
outside-checkout files were intentionally created; this is not a claim that every
initial test process write was confined to the checkout.

Independent security review approved these CI additions with no concrete blockers.
The reviewer reran all 53 tests, 132 × 2 style paths / 310 sections, archive and
consumer verification, actionlint, shell syntax, and synthetic Git identity checks.
The archive hash above reproduced unchanged. Local evidence:
`.work/security-ci-review.QP0gHC/check.log`. This approval covers bounded CI
preparation, not publication or hosted Linux execution.

Remaining operator gates: commit the entire approved tree and per-version notes,
configure/enforce repository/environment reviewer protections and tag protections,
prove exact-commit remote CI/Linux isolation, complete manual browser acceptance,
and only then enable tag publication and approve the verified artifact. Publication defaults disabled (`RELEASE_PUBLICATION_ENABLED` must be
explicitly set after setup). An environment name alone guarantees no approval.
See the first-release runbook; no release has been created by this phase.
