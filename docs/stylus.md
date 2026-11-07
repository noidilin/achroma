# Stylus production and customization

Catppuccin supplies website rules; Achroma supplies the palette. Latte is Achroma
Light and Mocha is Achroma Dark. Keep those identifiers: upstream branches and
native `color-scheme` depend on them. Frappé and Macchiato remain untouched
Catppuccin palettes. Website/browser settings decide appearance, not an Achroma
shell variable. This extraction does not redesign selectors or upstream behavior.

The original 134-style snapshot yields 132 styles. Codeberg and PythonAnywhere
are excluded because they import precompiled hardcoded themes rather than
variable-based dependencies. Both exclusions appear in the report. Existing
copies are not removed by reimport; disable them manually if desired.

Default filters come from the versioned `applications/stylus/filters.lock.json`,
a **canonical derived build input** transcribed from the independently approved
macOS native outputs. It is not a diagnostic cache and is hashed in the release
manifest and native build fingerprint. The lock binds the complete resolved
variant/role palette digest and exactly its 52 unique colors. Missing, stale,
malformed, duplicate-key or incomplete locks fail closed, including when an older
successful output exists. No normal build silently invokes the fitter.

Each entry contains six rounded emitted parameters in this order: invert percent,
sepia percent, saturate percent, hue degrees, brightness percent, contrast percent.
The version-1 validator enforces exact fields, numeric types (not booleans), finite
values, four-decimal quantization, fitter bounds, provenance digest shapes and
exact color coverage. It reapplies the emitted rounded coefficients to black and
requires both the recorded rounded error and the existing maximum absolute sRGB
channel tolerance of **8/255**. Approved defaults measure at most **0.478/255**.
This numerical check does not establish browser rendering equivalence.
`filters-v1.json` cache files remain write-only diagnostics, never source inputs.

### Why the default coefficients are locked

Hosted Linux CI exposed an inherited fitter portability defect, not an extraction
serialization change. At the committed extraction checkpoint, `filters.py` was
byte-identical to dotfiles revision `530cad951a3f1e401774839f3c8a2853240341b1`.
For light green `#4f6b4f`, a one-ULP platform `sin` difference changed the first
restart's search trajectory: with saturation zero, mathematically irrelevant hue
rotation still introduced matrix-rounding noise, flipping a strict loss comparison.
Linux stopped at that restart; macOS selected a later restart. Only that one CSS
filter differed (once in the library, embedded in all 132 styles).

Broad rounding/tolerance changes altered other approved filters. Rather than
redesign the optimizer, the approved repair locks the already-reviewed default
coefficients identically on every platform. No platform-specific baselines or
color/style changes are accepted. The seeded custom fitter remains available
explicitly, but **its output is not guaranteed bitwise portable**; seeding alone
cannot normalize platform libm behavior. See the detailed evidence in
[validation](validation.md).

## Custom source release

Start with a source checkout. Edit `applications/stylus/mapping.json`'s `accent`
(default `rosewater`) to another supported chromatic role, or edit canonical
palettes for your own customization. An accent-only change can keep the default
lock when resolved palette values/roles are unchanged. Palette/mapping changes
invalidate the lock. For explicit experimentation only, build with a separate local
semantic version, explicit output/cache paths, and `--fit-custom-colors` on
`tools/build.py` (or the low-level builder). This intentionally bypasses the lock
and uses the platform-dependent seeded fitter; it never happens automatically.
Before promoting changed defaults, follow the reviewed lock-refresh process below.
Run archive verification, compiler checks and the consumer example on candidates.
The extraction fixture equality test deliberately fails after intentional color
or accent changes: review and update the customization's fixtures explicitly,
never silently bypass regression tests. No dotfiles, runtime home palette, or
hosted-library change is needed. Record the source revision plus manifest input
hashes; an uncommitted source build is a local candidate, not a published release.

For low-level tests, `applications/stylus/build.py build` requires explicit
`--config`, `--output`, `--cache`; config is a disposable staging directory with
`palette.json`, `mapping.json`, `filters.lock.json`, and `vendor/` (the lock is not
required only for explicitly opted-in custom fitting). Normal users should use the root
entry point, which generates this adapter from canonical JSON automatically.
`check --output ...` verifies hashes/safety, not compilation; `examine <file>`
inspects the export. No commands default to HOME/XDG data destinations.

## Explicit reviewed filter-lock refresh

Ordinary build/check/release commands never refresh the lock. For an intentional
palette/role update, the maintainer must:

1. Review the source palette/mapping change and produce a **new scratch candidate**
   with `--fit-custom-colors`, a distinct semantic version and full source revision.
   Record the Python/OS/architecture used; custom fitting is platform-dependent.
2. Verify its archive, compile all styles in both paths, inspect the native filter
   changes/errors and complete appropriate browser acceptance. Obtain approval of
   these candidate bytes before promoting any coefficients. Do not copy a
   disposable `filters-v1.json` cache or bless separate per-platform output hashes.
3. Transcribe the six **emitted four-decimal parameters** and `max_channel_error`
   from the approved candidate's `reports/stylus-build.json` into the lock's
   `parameters`/`maxChannelError` records. Preserve exact resolved-color coverage.
   Set `resolvedPalettesSha256` to `filters.palette_digest(resolved_palettes)`;
   this is SHA-256 of the UTF-8 resolved variant/role JSON with sorted keys and
   separators `(',', ':')`, not of the raw palette files. Keep `schemaVersion: 1`
   and the corresponding fitter version unless a separately reviewed format or
   algorithm change actually requires a version update.
4. Update provenance with the approved candidate's full source revision, external
   archive checksum, native artifact hashes, runtime and review note. These fields
   describe the **source evidence**, not the subsequent locked rebuild (which has
   new input hashes and a different report fingerprint). Uncommitted evidence must
   be explicitly identified as local, not represented as a published release.
5. Build again **without** `--fit-custom-colors`. Validate the lock, compare native
   bytes to the approved candidate, run the complete CI/compiler/consumer checks,
   and reproduce default output across available platforms. Update extraction
   fixtures only for explicitly approved intentional native/color changes, never
   merely to bypass an unexplained mismatch. Review the source/lock/provenance
   diff together before committing and obtain exact-commit hosted CI proof.

The initial lock uses the previously accepted `0a1c0b12…` local candidate as
provenance and preserves both approved native hashes unchanged. It is a deliberate
new source input, separate from caches and from the frozen legacy library.

## Explicit upstream refresh (network allowed only here)

```sh
python3 -B applications/stylus/build.py update \
  --vendor-dir applications/stylus/vendor --commit <full-Catppuccin-userstyles-SHA>
```

Review every snapshot/lock diff and upstream license change. The standard-library
revision and export checksum are independent; mutable download URLs are only
provenance, never release-time fetch inputs. Refresh is not called by build/check.
New imports or unfamiliar library structure fail closed. Refresh tests mock
network responses; normal generation verifies every locked checksum first.
Rebuild and compile all styles before promotion. Review syntax CSS license notices
in `licenses/` when updating those dependencies.

## Manual browser gate

1. Export the **live** Stylus backup before any import.
2. Import the candidate into an isolated profile, never automatically.
3. Review enabled states, inclusion patterns, site-specific variables, global
   `updateInterval = 0`, and dark/light transitions without reinstalling.
4. Review text-heavy sites, dashboards, appearance toggles, SVG/filter/syntax
   examples, focus/hover/selection, borders, disabled states, and contrast.
5. Main-profile import requires separate approval. Rollback restores the live
   backup, not merely repository files.

Styles contain no runtime Less/CSS imports; external images/fonts can still need
network. Legacy hosted `lib/lib.less` remains unchanged and is not used by new
bundled exports. Existing extension state and visual coverage remain unverified
for this standalone pilot.

Attribution: extracted from the Stylus implementation in
[the dotfiles repository](https://github.com/noidilin/dotfiles), revision recorded
in `fixtures/extraction/provenance.json`. Catppuccin Userstyles, Python/Pygments,
PrismJS, and HighlightJS theme MIT notices are preserved under `licenses/`;
UserCSS author/license metadata is retained. `licenses/provenance.json` records
immutable sources for supplementary MIT notices collected during extraction;
these license-source revisions do not claim the CSS snapshots share those source
revisions. Snapshot bytes remain independently pinned by the original lock.
