# Optional Achroma complement UserCSS

New source builds include **`themes/stylus/achroma-complement.user.css`** inside the
release ZIP. This is a separate, optional plain-CSS UserStyle, not an extra record
in `themes/stylus/import.json`. The 132-style Catppuccin-derived backup, its native
hashes, filters and settings remain unchanged. The complement does not contain a
Stylus settings record or change global `updateInterval`.

## Source and ownership

The original personal style is
[UserStyles.world style 25419](https://userstyles.world/api/style/25419.user.css),
version `20251204.06.12`, declared MIT. Its exact original bytes (including line
endings) are pinned under `applications/stylus/complement/upstream.user.css` with
URL, version, license and SHA-256 in `upstream.lock.json`. The vendored original
is evidence, not executable build input or the file to install. In particular,
its `@namespace ?` and hardcoded colors are not copied into the generated style.

`style.css.tmpl` is the maintained adaptation. `tools/complement.py` generates its
colors offline from the canonical 66-key palettes, not the Catppuccin accent-role
remapping. The release manifest hashes the template, raw source, lock, renderer,
and standalone output. The output's comment records the original source URL and
checksum, and preserves `@license MIT`. Its namespace is
`https://github.com/noidilin/achroma/complement`; its version follows the Achroma
release version, independently of the original style's version.

## Behavior and color mapping

The browser's `prefers-color-scheme` selects light or dark. Light is the default;
a dark media block overrides the same namespaced CSS variables. No runtime import,
network dependency, Less preprocessor, upstream update URL or fitting is needed.
This setting is independent of any site's own appearance toggle and the main
Catppuccin backup's flavor selections. A dark site under a light browser preference
can therefore get light complement colors; test your actual appearance settings.

The original selectors and site scope are retained, with CSS nesting flattened:

- Global text shadow and text-rendering/stroke rules, except the original
  `monkeytype.com`, `tweakcn.com`, and localhost ports 3000/5173 exclusion expression.
- Global `.leechblock-timer` styling. **The rendering exclusions do not exclude
  the timer or global variable definitions**, matching the original timer scope.
- `www.youtube.com` progress colors.
- `linux.vbird.org` page overrides, including the original hidden footer/history/
  image selectors, widths, spacing, font styles and code font override.
- `boot.dev` background gradients.

Colors use these canonical role references in both modes:

| Original dark-oriented colors | Canonical roles |
| --- | --- |
| `#151515`, `#191919`, `#1e1e1e` | `crust`, `mantle`, `base` |
| `#242424`, `#686868`, `#aaaaaa`, `#dcdcdc`, `#eaeaea` | `mono04`, `mono14`, `mono20`, `mono24`, `mono25` |
| `#353535`, selection `#404040` | `surface1`, `surface2` |
| `#4e4e4e`, `#5d5d5d`, `#707070` | `overlay0`, `overlay1`, `overlay2` |
| `#878787`, `#9d9d9d`, `#b3b3b3` | `subtext0`, `subtext1`, `text` |
| YouTube `rgb(240,240,240)`, `rgb(180,180,180)` | `mono25`, `text` |

Selection and progress colors deliberately use nearby canonical roles instead of
adding arbitrary colors to the palette. These mappings intentionally change light
mode and slightly normalize those dark colors. The code font is normalized to
`"CommitMono Nerd Font", monospace`; no font is downloaded. Commented-out original
experiments are not active rules. These are personal overrides, not a claim of
contrast compliance or universally improved readability.

## Build and manual acceptance

Use the normal source build, then open/copy the generated `.user.css` into Stylus
**only in an isolated profile first**. It is never installed, imported or enabled
automatically. If the original personal style is installed, disable it in that
profile before comparing: its different namespace can otherwise coexist and
conflict. Back up live Stylus state before any main-profile change.

Validate light/dark preference transitions, readability and rendering exclusions,
LeechBlock timer appearance, YouTube progress, Vbird's hidden content/navigation/
code blocks, and Boot.dev backgrounds. Check interactions with the main style
bundle and site-specific toggles. Text shadow/stroke and hidden content are broad
personal choices; disable the complement if they impair readability or hide
needed content. Rollback disables/removes this optional style or restores the
live backup; do not modify the frozen legacy `lib/lib.less`.

CI parses UserCSS metadata and the CSS AST, checks all five document sections,
resolves every used color against both palettes, and tests the original exclusion
expression. Python tests cover offline deterministic rendering, custom palettes,
source/lock corruption, metadata/import rejection, mocked update checks and
snapshot failures; archive verification checks palette/metadata consistency even
after payload checksums are recomputed. None of that establishes visual acceptance
or actual browser import. No browser state was changed during implementation.

## Explicit original-source update check

Network access is limited to these explicit commands, never normal build/check:

```sh
python3 -I -B tools/complement.py check-upstream
```

Exit 0 means unchanged original bytes, 1 means changed bytes requiring review,
and 2 means an error. Byte comparison detects edits even if the author leaves the
version unchanged. It does not mutate snapshots, templates, output or browser
state. To stage a changed original into a **new scratch directory**:

```sh
python3 -I -B tools/complement.py snapshot-upstream \
  --output .work/complement-upstream-review
```

Review the source diff and MIT declaration before replacing the vendored source
and lock together. Manually port accepted selector/behavior changes into the
palette-aware template; never overwrite it with the original's hardcoded CSS.
Rebuild, run the complete check suite, and repeat isolated browser acceptance.
License/identity drift fails staging and requires a separate manual review.

The scheduled Catppuccin refresh workflow does not update this personal source.
Its narrow vendor allowlist and trust boundary are unchanged. No automatic
upstream updates, publication or browser import are added here.

## Consumer compatibility

The new optional ZIP member and four additional build-input hashes are an
all-or-nothing manifest extension. The updated producer verifier also accepts the
original v0.1.0 contract; old strict consumers do not know this extension. A future
release containing it must use a newly reviewed **minor version before 1.0** and
coordinate consumer verifier/allowlist support before repinning chezmoi. Do not
republish v0.1.0, change its pin, or assume the existing installer exposes the new
standalone file. Chezmoi's current pinned release and live candidates are untouched.

The historical Nushell download/hex-replacement workflow is not this producer.
See [Stylus production](stylus.md), [consumption](consumption.md) and
[release policy](release.md) for the separate bundled export and release gates.
