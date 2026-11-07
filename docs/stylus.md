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

Filters use seeded stdlib-only fitting against resolved colors. Cache files are
only diagnostics and never trusted generation inputs. The maximum permitted
absolute sRGB channel error is 8/255; the baseline real palette measures less than
0.478/255. This numerical check does not establish browser rendering equivalence.

## Custom source release

Start with a source checkout. Edit `applications/stylus/mapping.json`'s `accent`
(default `rosewater`) to another supported chromatic role, or edit canonical
palettes for your own customization. Build with a separate local semantic version
and explicit output/cache paths, then run local CI/compiler checks from README.
The extraction fixture equality test deliberately fails after intentional color
or accent changes: review and update the customization's fixtures explicitly,
never silently bypass regression tests. No dotfiles, runtime home palette, or
hosted-library change is needed. Record the source revision plus manifest input
hashes; an uncommitted source build is a local candidate, not a published release.

For low-level tests, `applications/stylus/build.py build` requires explicit
`--config`, `--output`, `--cache`; config is a disposable staging directory with
`palette.json`, `mapping.json`, and `vendor/`. Normal users should use the root
entry point, which generates this adapter from canonical JSON automatically.
`check --output ...` verifies hashes/safety, not compilation; `examine <file>`
inspects the export. No commands default to HOME/XDG data destinations.

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
