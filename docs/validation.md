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

## Hosted Linux failure and approved coefficient-lock repair

The operator subsequently committed/pushed the approved extraction and CI tree as
`3e091fbc61bfd5fdaf5df38bc34727b034362d5f`. Hosted
[CI run 42375625742](https://github.com/noidilin/achroma/actions/runs/42375625742)
completed pinned runtime setup, locked npm preparation and network-namespace setup,
but failed `test_real_native_bytes_match_baseline`. All 22 relocated tests and the
other 30 contract/CI tests passed; the two isolated Linux builds matched each other.
The failure occurred before the required real compiler step, so this run is not a
successful full CI gate. Logs were fetched read-only with `gh run view --log-failed`
to `.work/linux-failure.log`; that failed run had no uploaded artifacts.

### Exact root cause and scope

The already-running Colima VM provided preinstalled Linux arm64 Python **3.12.3**.
Without installing any tools or images, its unmodified build reproduced the hosted
Linux x64 Python 3.13.13 ZIP exactly:
`2541039fcb9513e10b58532b57c1fe24179efa7f86130c5e72f23fc489608305`
(using the fixture source revision/version). This supplied the missing native
outputs for byte-level inspection.

Only the fitted filter for **light green `#4f6b4f`** differed. Replacing that single
CSS string restored the approved `lib.less` bytes exactly; replacing its 132
embedded copies restored `import.json` exactly. No palette values, selectors,
metadata or other filters differed. Proof: `.work/linux-investigation/native.diff`,
`report.diff`, and `byte-difference-proof.log`.

Traces found the first numeric/branch divergence at search trial index **54**,
restart **0**, scale **0.08**, hue axis, negative step, with **saturation zero**:

- Hue input: `0x1.4e2746ef4e6f0p+1`.
- macOS `sin`: `0x1.034878b9b6c0dp-1`; Linux: `0x1.034878b9b6c0cp-1` (one ULP).
  `cos` was identical.
- Current loss: `0x1.06985f934dc52p+9`.
- macOS trial loss: `0x1.06985f934dc54p+9` (rejected).
- Linux trial loss: `0x1.06985f934dc4fp+9` (accepted).

Hue rotation is mathematically irrelevant at zero saturation, but floating-point
matrix evaluation introduced spurious improvements. Linux accepted its first
restart, emitting `[34.6405, 83.5250, 80, 70.9869, 104, 149]` with error **0.0066**;
macOS continued through restart 2, emitting approved
`[16.7705, 100, 178.4, 72.3307, 167.88, 71.02]` with error **0.478**. Parameters here
are invert/sepia/saturate percentages, hue degrees, brightness/contrast percentages.
Both satisfy the existing tolerance, but accepting the Linux bytes would silently
change reviewed output. This is an **inherited numerical portability defect**:
`filters.py` at commit `3e091fb` is byte-identical to dotfiles revision
`530cad951a3f1e401774839f3c8a2853240341b1`, SHA-256
`b47a3a19a685713e3f360bf190abaae5188a25862ec0ea4ac3b2b91264a59c18`.

Evidence: `mac-trace.json`, `linux-trace.json`, `first-branch.json`,
`{mac,linux}-components.log`, and `root-cause-summary.log` under
`.work/linux-investigation/`. Scratch tolerance/trig-rounding experiments either
retained the mismatch or changed additional approved filters; none were promoted.

### Approved bounded repair

The user explicitly selected a **versioned lock of approved default coefficients**,
not platform-specific baselines or an optimizer redesign. New
`applications/stylus/filters.lock.json` records all 52 resolved colors, rounded
coefficients, measured errors, the complete resolved-palette digest, fitter/schema
versions, and provenance linking the independently accepted `0a1c0b12…` candidate
and original native hashes. This is a new **canonical derived build input**, not
trusted cache data. The manifest now requires/hashes this 23rd build input.

Normal builds validate exact schema/types/fields, duplicate-key rejection, exact
palette/role digest and color coverage, finite bounded six-parameter shapes,
four-decimal quantization, recomputed emitted-filter tolerance and recorded error.
Missing/stale/invalid locks fail before cached-output reuse; there is no fallback
to fitting. The original fitter remains only behind explicit `--fit-custom-colors`
for custom source experiments, documented as potentially platform-dependent.
Reviewed refresh instructions are in `stylus.md`. Existing native baseline equality
assertions and all original fixtures remain unchanged.

### Repair validation (uncommitted local evidence)

- macOS Python **3.13.13**, Node **22.17.1**:
  `python3 -I -B tools/check.py --output .work/linux-investigation/mac-final --cache
  .work/linux-investigation/mac-final-cache --version 0.1.0-dev --source-revision
  3e091fbc61bfd5fdaf5df38bc34727b034362d5f` passed **60 Python tests**, archive
  verification, **132 × 2 style paths / 310 sections**, and the consumer example.
  Log: `.work/linux-investigation/mac-full-check-final.log`.
- Existing Colima Linux arm64 Python **3.12.3**, in a fresh `sudo unshare --net`
  namespace with privileges dropped to the VM user, ran all **60 Python tests**,
  default build, archive verification and consumer example successfully. Only
  loopback was visible; scratch/HOME/TMPDIR remained checkout-local. Exact script:
  `.work/linux-investigation/check-linux-final.sh`; log:
  `.work/linux-investigation/linux-isolated-check-final.log`. Node is not installed
  in that VM; no compiler-on-Linux execution is claimed.
- The seven new lock regressions cover malformed/stale/missing/duplicate locks,
  palette/role and exact-color coverage, parameter/error validation, invalid-lock
  failure despite existing successful output, lock manifest hashing, and the actual
  Linux one-ULP `sin` value. The latter reproduces the custom search mismatch and
  proves default generation preserves baseline bytes without calling the fitter.
- macOS and Linux final archives are byte-identical, SHA-256
  `7e5a86cdbae824822ee63637de5b80aebcd6671286f96fbd7d0cc9b03803b40a`.
  The archive changes because source input hashes, the report fingerprint, and the
  supplied revision now differ; **native outputs remain byte-identical** to the
  approved candidate: `import.json` = `84cb4b1cfba2cb41076c8e2984cd254feded67b36a26b982e2e40db7ae7615b1`,
  `lib.less` = `8e0bd1e98e92c7560f175132838d58e2103065514997f281a8916e3b93274717`.
  Linux-generated native bytes were also compiled with macOS Node 22.17.1:
  `.work/linux-investigation/linux-output-compiler.log`.
- Frozen legacy hash remains `73f2609f5346c5bab0afa0bed0db4b1b9a7eff83b94d1321bdf18194acf21f22`;
  `.work/review-fixed` and its original archive hash are preserved. No palette,
  mapping, vendor, baseline-fixture, workflow or Pages changes were made by this
  repair. No files staged; no commits/pushes/tags/publication/settings changes or
  system tooling installations performed by the repair worker; dotfiles is read-only.

These are dirty-tree local candidate hashes, **not release provenance**. Independent
review approved the repair without required changes and reproduced all 60 tests,
132 × 2 compiler paths / 310 sections, native hashes and the candidate ZIP using
macOS Python 3.15.2 / Node 26.13.0. Local reviewer evidence:
`/tmp/achroma-lock-review.5qGlw0`. Operator-authorized commit/push must precede a
successful hosted Linux **x64 Python 3.13.13 / Node 22.17.1** rerun on the exact new
commit. That gate, environment/operator prerequisites and browser acceptance remain
outstanding.
The hosted action Node20 deprecation warnings are nonblocking and deferred outside
this numerical repair; no action upgrades were bundled into it.
