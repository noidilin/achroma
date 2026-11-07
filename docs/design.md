# Achroma design principles (historical TUI guidance)

How to map the achroma palette onto a terminal app, digested from the two
reference implementations that have had the most attention paid to them:

- **neovim** — `noidilin/nvim`, `lua/theme/lua/` (`lush_theme/_primitive.lua`
  holds the same palette as `.chezmoidata/colors.yml`; `_semantic.lua` and
  `_component.lua` are the design-token layers; `lush_core/*.lua` and
  `lush_plugin/*.lua` are the specs; the lualine table lives in
  `lua/plugins/ui.lua`).
- **wezterm** — `noidilin/wezterm`, `config/theme.lua` plus the `events/*`
  tab-bar and status-line handlers, `utils/palette*.lua`.

This guidance is preserved from the dotfiles extraction baseline (see
`fixtures/extraction/provenance.json`). The application examples describe existing
external implementations, **not** additional themes shipped by this Stylus pilot.
Canonical source here is `palette/{dark,light}.json`; this is design guidance,
not a request to redesign the mechanically extracted Stylus output. Switching,
local composition, and runbooks remain in the
[dotfiles documentation](https://github.com/noidilin/dotfiles/tree/main/docs).

## 1. The palette is addressed by role, never by lightness

`mono00`–`mono25` run background-side → foreground-side in **both** variants.
`mono02` is near-black in dark and near-white in light. So a theme body says
`mono13` and gets a readable mid-gray either way, and rendering the light
variant is just passing the other table — the wrappers do nothing else.

This file speaks in rung numbers, as neovim and wezterm do, because the
arguments below are arithmetic on the ramp. In
`palette/{dark,light}.json` a rung that has a role is keyed by it (`mono02` is `mantle`,
`mono21` is `text`, `red00` is `red`); the translation table is in
the dotfiles Achroma documentation.

Same for the chromatic ramps: they are re-derived per variant, not inverted, so
`red00` is a *readable red on the current background* in both. Two consequences
worth internalising:

- An **inverted chip** (chromatic or mid-mono fill, `mono02` as its text)
  survives mirroring automatically. Nothing about it has to branch.
- A **naive mirror of a surface does not survive**, because the light ramp is
  compressed at the background end. That is what §3 and §4 are about.

## 2. Two metrics, two jobs

Text is judged in WCAG contrast ratio. Surfaces are judged in **ΔL\*** (CIE
lightness difference), because contrast ratio is nearly flat down at the
background end of the ramp and stops discriminating exactly where surface work
happens. wezterm's `config/theme.lua` states its surface decisions in dL\* for
this reason; copy that habit.

Working floors, as actually applied across the repo:

| what | metric | floor |
| --- | --- | --- |
| body text, labels, anything read | contrast | 3.5:1, prefer ≥ 4.5:1 |
| deliberately faded text (done/archived/comment) | contrast | may sit 1.6–2.5:1 |
| decoration (rules, splits, scrollbars) | contrast | 1.6–2.5:1 by design |
| a surface that must read as *raised* | ΔL\* | ≈ 8 |
| a surface that must read as *a different plane* | ΔL\* | ≈ 10–13 |
| status-bar-style flush fill | ΔL\* | 2–4 |

And the compression itself, ΔL\* off `mono02` (the ground every tool draws on,
since that is what ghostty sets the terminal background to):

| rung | dark | light |
| --- | --- | --- |
| `mono03` | 2.5 | 3.5 |
| `mono04` | 5.4 | 4.2 |
| `mono05` | 8.3 | 4.5 |
| `mono06` | 11.1 | 6.3 |
| `mono07` | 13.4 | 8.1 |
| `mono08` | — | 10.2 |
| `mono09` | 18.8 | 12.3 |

Read off the table: the light ramp needs to climb roughly **two rungs** to buy
the same step the dark ramp gets in one. `mono05` is a raised plate in dark and
invisible in light; `mono07` is the light equivalent. This is not a fudge, it is
the same number on both sides (8.3 vs 8.1).

## 3. The parity rule

When a slot's *meaning* is "one step off the ground", the two variants must
match in perceived step, not in rung number. Every repo theme body therefore
keeps colors as `{{ .c.<role> }}` and takes the direction-sensitive ones from an
`ink` dict the wrappers fill in per variant. wezterm does the same thing with a
local `ink` table chosen by `is_light`; neovim does it with
`local light = require(...).is_light` and `light and X or Y` at the few groups
that need it. Same idea, three spellings.

Keep the dark branch equal to the dark value that was already there, so a
refactor is a no-op for the dark render — both reference configs note this
explicitly, and it makes review trivial.

## 4. The direction-sensitive catalog

These are the slots that have needed an override, with the pairs that work.
Start from this table rather than rediscovering it:

| role | dark | light | why |
| --- | --- | --- | --- |
| raised plate (active tab, mode pill, palette panel) | `mono05` | `mono07` | 8.3 / 8.1 dL\* |
| selection fill | `mono06`–`mono07` | `mono08`–`mono09` | 11.1 / 10.2 dL\*; keeps selected text ≥ 4.8:1 |
| list-cursor fill | `mono05` | `mono07` | neovim's own light `PmenuSel` override |
| split / window border | `mono07` | `mono10` | repo-wide chrome convention |
| float border (`FloatBorder` class) | `mono09` | `mono10` | 1.72 / 1.63:1 |
| graded rules (hairline < frame < rule) | `mono09`/`mono10`/`mono11` | one rung up each | leaf has seven line slots; one `border` was not enough |
| faint foreground (scrollbar, new-tab, inactive) | `mono09`–`mono11` | `mono11`–`mono13` | `mono09` is 1.72:1 dark but 1.38:1 light |
| inverted-chip text / cursor fg | `mono12`-ish or `mono25` | `mono02`-ish | wezterm's `cursor_fg`, neovim's `on_fill` — pick the end *opposite* the fill |
| ANSI `black` / `white` | `mono10` / `acc07` | `mono19` / dark-palette `acc06` | must **not** invert, or programs printing in them vanish; light white borrows the dark warm tones, already the right lightness |

Two rules hide inside that last row and are worth stating plainly:

- **Pair a fill with the opposite end of the ramp, not with a fixed rung.**
  neovim's `_component.lua` keeps `on_fill = light and mono02 or mono12` for
  exactly this; wezterm's `cursor_fg` is `mono25` in dark and `mono02` in light
  because the mirrored value gave a 2.82:1 cursor.
- **"Do not invert" is a legitimate answer.** Anything whose name encodes a
  direction (ANSI black/white) or whose consumer is arbitrary third-party output
  is pinned, not mirrored.

## 5. The foreground ladder

The single most transferable thing from the neovim theme: which rung means
what. Text almost never sits outside this ladder.

| rung | meaning | seen as |
| --- | --- | --- |
| `mono21` | **terminal default** foreground — text the app does not own | wezterm `foreground`, zebar `--text` |
| `mono19`–`mono25` | emphasis tier: headings, keywords, active labels | `@markup.heading` mono19, `_md_h1` mono25, wezterm active tab mono21, mode-pill label mono24 |
| `mono16` | **an app's own body text / prose** | `Normal`, `@markup`, `StatusLine` fg |
| `mono17` | status-bar text, one notch forward of the editor | lualine section fg |
| `mono15` | secondary text: hints, labels, links, counts | `info`, `@markup.link`, `_string`, `ObsidianDone` |
| `mono12`–`mono13` | faded: comments, line numbers, struck-through, done | `_comment`, `LineNr`, `@markup.strikethrough`, wezterm status segments |
| `mono09`–`mono11` | backdrop: `NonText`, `Title`, indent guides, flash backdrop — **not for text** | `_component.lua` flags `mono09` as unusable as a plain fg |

Note the deliberate split between `mono21` and `mono16`. A terminal hands
`mono21` to programs it cannot style; an app that draws its own content body
uses `mono16` and spends the brighter rungs on emphasis. Pick the row that
matches what the tool actually is.

## 6. The chroma budget

The neovim specs use exactly **four** chromatic slots, and always for alerts:

| slot | meaning | groups |
| --- | --- | --- |
| `red00` | error | `error`, `ErrorMsg`, `GitSignsDelete`, `ObsidianImportant` |
| `orange00` | warning | `warn`, `WarningMsg`, `SpellCap` |
| `yellow00` | change / attention | `GitSignsChange`, `SpellLocal` |
| `green00` | ok / added | `ok`, `GitSignsAdd` |

Blue, cyan and magenta appear only where a *protocol* demands them — wezterm's
ANSI/brights arrays, file-type icon colors, a progress state — never as a
design choice. The `01` rung is the emphasis tier of the same hue (wezterm's
`brights`, bufferline's selected diagnostics), not a different meaning.

Everything else that needs to be "not gray" uses the **warm accent ramp**,
which is achroma's identity:

| slot | used for |
| --- | --- |
| `acc07`–`acc08` | attention labels, flash labels, top headings, ANSI white |
| `acc06` | an open todo marker (`ObsidianTodo`) |
| `acc04`–`acc05` | link icons, constants, prompts, raised-chip fills |
| `acc02`/`accDim02` | containers and references: `Directory`, links, properties |

`acc02` and `accDim02` are within a percent of each other — fine in neovim,
where they never co-occur, but if a tool shows two accent-colored token types in
the same row, separate them by at least two rungs.

So the decision order for a new colored thing is: **is it an alert?** → one of
the four chromatic slots. **Is it identity or a reference?** → the accent ramp.
**Otherwise** → the mono ladder.

## 7. Chips, fills and highlights are gray

Both references highlight with **mono fills**, not colored ones:

- neovim `Search` fills `mono10`, `CurSearch` `mono07`, `IncSearch` inverts to
  `mono02` on a `mono19` fill, `FlashCurrent` on `mono17`,
  `ObsidianHighlightText` on `mono09`.
- lualine's mode chips are `mono03`/`mono15`/`mono21` fills — never the accent.
- wezterm's mode pill is the raised plate (`ink.raised`) with a `mono24` label.

Construction rules that fall out of that:

- An inverted chip = **mid-mono fill + `mono02` text**. `mono17` reads at
  4.89:1 dark / 6.24:1 light, `mono19` at 6.48 / 7.89. Use the brighter one for
  transient hits (a search match), the dimmer for persistent chrome (a mode
  badge).
- If a chip has **end caps drawn as glyphs** over the bar, the cap's *fg* must
  equal the pill's *bg*, or the caps detach (wezterm's `scircle`).
- **Spell every slot out.** wezterm's `inactive_tab` entries exist because
  anything left unset falls back to built-in defaults that are dark regardless
  of scheme — correct under achroma, wrong under achroma-light. Same failure
  class as leaf silently ignoring an unknown key.

## 8. Surfaces: everything on mantle

`mono02` (mantle) is what ghostty sets the terminal background to, so a TUI's
main surface is mantle — the app then disappears into the terminal instead of
floating one step above it on base. leaf, jjui, pi and tuxedo all do this, and
wezterm's window and tab-bar backgrounds are mantle for the same reason.

The consequences are worth accepting deliberately:

- Panes and floats have **no fill of their own** and are delimited by a border
  or a separator. That is neovim's own float construction (`NormalFloat` is
  mantle, `FloatBorder` carries the edge).
- The status bar is the one surface that gets filled — `mono03` (base), a 2–4
  dL\* lift, which is what `StatusLine` and lualine look like.
- Selection still lifts clear, because selection fills sit 8–13 dL\* up.
- Base (`mono03`) is otherwise *unused* by most bodies. That is fine; it is a
  floor, not a slot that must be spent.

## 9. Checklist for a new tool

1. Read the app's theme source, not just its docs — enumerate every color key
   and find out which are foregrounds, which are fills, and which are *both*
   (tuxedo's `bg` doubles as the search chip's text color).
2. Map each key to the neovim group that does the same job, and take that rung.
   Where the app has no neovim analogue, find the nearest *semantic* one — a
   four-level priority ramp is a four-level severity ramp.
3. Record palette-role references and explicit variant overrides in the application
   mapping; keep personal behavior in the consumer. Cite the neovim/wezterm
   group next to each non-obvious choice. Do not introduce a general template engine.
4. Measure both variants: contrast for every fg × every bg the app can pair
   them on (including each row fill), ΔL\* for every surface. Check the floors
   in §2, and check that the *pairs* track across variants.
5. Verify against the running app, not just the render. The strongest check is
   **no color on screen from outside the theme** — most TUIs fall back silently
   to a built-in when a theme fails to parse, so foreign colors are how a broken
   render shows itself. Drive the app under a pty, capture the SGR sequences and
   decode them back to hex.
6. Flip only the pointer (or the env var) and confirm every on-screen color
   moves to the other render and back.
7. Record measurements and remaining visual checks in the application documentation.

## 10. How it landed

| tool | body text | main surface | selection | highlight | chroma used |
| --- | --- | --- | --- | --- | --- |
| leaf | `mono21` (markdown prose is the content) | mantle | `mono05` → `mono07` | `acc07` on selection fill | green/orange/red for status only |
| tuxedo | `mono16` (own prose, neovim ladder) | mantle, status bar on base | `mono07` → `mono09`, cursor row `mono05` → `mono07` | `mono19` inverted chip | `red00`/`orange00`/`yellow00`/`green00` only |
| jjui | `mono15` on mantle | mantle | `mono03`/`mono07` | `acc07` bold underline | none |
| wezterm | `mono21` (terminal default) | mantle | `mono06` → `mono08` | raised plate | full ANSI, by protocol |

The two rows that look inconsistent are the §5 split doing its job: leaf and
wezterm hand text to content they do not own (rendered markdown, arbitrary
programs) and use `mono21`; tuxedo and jjui draw their own rows and use the
`mono15`/`mono16` body rungs.
