# Achroma

Standalone dark/light palettes and offline Stylus UserCSS generation. This pilot
extracts the existing dotfiles implementation mechanically; other application
integrations, installation, and OS switching are not included. Release workflows
are prepared, but publication requires explicit operator setup and approval.

## Build without dotfiles

Requires Python 3.11+ (standard library only). No chezmoi, mise, populated home,
browser, or network is needed. From this source checkout:

```sh
python3 -B tools/build.py --output .work/candidate --cache .work/cache \
  --version 0.1.0-dev --source-revision "$(git rev-parse HEAD)"
python3 -B tools/verify.py .work/candidate/achroma-0.1.0-dev.zip .work/candidate/SHA256SUMS
```

Output must be absent or empty; use a fresh candidate directory for each build.
The output contains `payload/`, `achroma-<version>.zip`, and external `SHA256SUMS`.
Do not install directly over live data. Explicit output/cache paths are required;
HOME/XDG variables are never release destinations.

**Browser warning:** importing the export sets Stylus's **global**
`updateInterval = 0`, affecting unrelated installed styles too. Export your live
backup first and test manually in an isolated profile. No command here imports
browser state. New styles have no upstream update URLs or runtime Less/CSS imports;
website image/font URLs are not bundled. Reimport does not delete excluded styles.

## Local CI contract

Only preparation needs network. Locked npm dependencies are development-only:

```sh
npm ci --prefix tests/stylus --cache .work/npm-cache --ignore-scripts --no-audit --no-fund
python3 -B tools/check.py --output .work/checked --cache .work/check-cache \
  --version 0.1.0-dev --source-revision "$(git rev-parse HEAD)"
```

This runs the Stylus adapter tests, producer contract regressions (including two
isolated checkout/home/cache builds), archive verification, all **132 styles × 2
flavor paths**, 310 document sections, helper fixtures, and the plain Python
consumer example. The separate optional complement is also checked for UserCSS/CSS
syntax, five document scopes and canonical light/dark palette values (see below).
Local generation has a Python network audit hook and the compiler
has connection guards; these are not whole-process isolation. Linux CI runs the
**entire check process** in a fresh network namespace after online preparation.
Missing Node/dependencies or namespace setup fail rather than installing or
bypassing checks. Browser import/visual coverage remains a separate manual gate.

[CI](.github/workflows/ci.yml) checks PRs and branch pushes with read-only permissions,
Python 3.13.13, Node 22.17.1, and SHA-pinned actions. It archives verified bytes and
the actual checked-out revision. The [tag-only release workflow](.github/workflows/release.yml)
uses `v0.1.0` → producer version `0.1.0` (semantic prereleases also supported).
Publication is disabled unless the operator explicitly enables it **after** setting
up required reviewers on the `release` environment. See the
[first-release runbook](docs/release.md); an environment name alone enforces no approval.

## Optional personal complement

Source builds also package `themes/stylus/achroma-complement.user.css` as a
**separate optional style**, leaving the 132-style import unchanged. It adapts the
personal style's text rendering, LeechBlock, YouTube, Vbird and Boot.dev overrides
to canonical palettes and browser light/dark preference. Import is manual; broad
rendering and hidden-content rules require visual review. Its original source is
pinned separately and can be checked with `python3 -I -B tools/complement.py check-upstream`.
See [complement documentation](docs/userstyle.md) for behavior, provenance, update
checks and the consumer-compatibility gate before a future release.

## Source ownership

- `palette/{dark,light}.json`: canonical 66-key palettes, lowercase `#rrggbb`.
- `applications/stylus/mapping.json`: role references and default accent.
- `applications/stylus/vendor/`: unchanged locked snapshots and MIT license.
- `applications/stylus/{build,filters}.py`: stdlib generator and validated default filters.
- `applications/stylus/filters.lock.json`: versioned, reviewed default coefficients
  preserving approved native bytes across platforms; never a diagnostic cache.
  Explicit custom-color fitting remains platform-dependent (see [refresh/customization](docs/stylus.md)).
- `applications/stylus/complement/`: original personal UserCSS snapshot, provenance
  lock, and maintained palette-aware template.
- `tools/complement.py`: offline optional-style renderer and explicit source-update checks.
- `tools/build.py`: disposable staging adapter and reproducible release packaging.
- `schemas/`, `fixtures/`, `tests/`: contract and extraction fidelity evidence.
- `licenses/`: preserved upstream MIT notices and license-source provenance.

`lib/lib.less` is a **frozen legacy hosted asset**, not a generated output. Its
bytes and existing GitHub Pages branch settings must remain unchanged. Generated
`payload/themes/stylus/lib.less` is a separate artifact.

See [consumption](docs/consumption.md), [Stylus and refresh](docs/stylus.md),
[design guidance](docs/design.md), [local release contract](docs/release.md), and
[validation checkpoint](docs/validation.md). The source extraction baseline is
recorded in `fixtures/extraction/provenance.json`; existing dotfiles switching and
installation remain in [the dotfiles repository](https://github.com/noidilin/dotfiles).
