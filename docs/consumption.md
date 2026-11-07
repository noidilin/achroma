# Producer/consumer contract v1 (pilot)

The exact `data/consumer.json` shape is defined in
[`schemas/consumer.schema.json`](../schemas/consumer.schema.json); a complete
representative instance is [`fixtures/consumer/consumer.json`](../fixtures/consumer/consumer.json).
The object has exactly these top-level fields:

```json
{
  "schemaVersion": 1,
  "release": {"version": "0.1.0-dev", "sourceRevision": "41572a8510f6ce8f567b12371d91016eec1a90f6"},
  "palettes": {"dark": {}, "light": {}},
  "mappings": {"stylus": {"dark": {}, "light": {}}}
}
```

The empty objects above abbreviate data, not optional fields. Each palette has
all 66 keys from `palette.schema.json`. Each mapping has exactly:

- `flavor`: `mocha` for dark, `latte` for light.
- `palette`: all 26 resolved browser roles, each `#rrggbb`.
- `usercssVariables`: value-level `lightFlavor`, `darkFlavor`, `accentColor` defaults.
- `settings`: `{"updateInterval": 0}` (the global import effect, not a per-site preference).

Aggregate palettes equal `palette/<variant>.json`; aggregate mappings equal
`mappings/stylus/<variant>.json`, including non-color defaults. Mapping palette
values equal the native build report's resolved palettes. Equality is tested.
Source roles `rosewater → acc07`, `flamingo → acc06` resolve from the same mapping
used by native generation. No personal `achroma-current` alias is required.

**No archive URL or archive checksum belongs inside this object.** A downstream
adapter injects its trusted versioned URL/checksum externally, after verifying
the archive. This prevents self-reference. Checksums establish integrity, not
independent authenticity. No installer/updater or dotfiles snapshot is changed by
this pilot.

## Palette only

Load `palette/dark.json` using any JSON reader; use role names, not guessed
lightness. There is no dependency on a producer template engine.

## Plain Python and explicit overrides

```sh
python3 -B fixtures/consumer/compose.py .work/candidate/payload
```

The example loads a resolved mapping and merges **only its variable-value object**
with a user override (`accentColor = blue`), with user values winning. It does not
write browser state. Native Stylus backups contain arrays and structured variable
records: never apply a universal recursive merge to them.

## Native file

`themes/stylus/import.json` is the native manual import candidate. It retains
upstream names, namespaces, enabled flags, selectors, custom inclusions, and site
variables; preserves the baseline global settings record; strips update URLs,
stale digests/sections; and bundles supported dependencies. Back up live Stylus
state and review global update policy before isolated-profile import. No OS
appearance setting or automatic import is supplied.

## Fragment

`fragments/stylus/{dark,light}.less` contains only resolved `@role: #rrggbb;`
declarations. It is an **incomplete Less variable fragment**, not a configuration,
UserCSS stylesheet, or replacement for the helper library. Include the chosen
variant in your own Less scope; later declarations of the same variable in that
scope win (Less lazy evaluation applies). It owns neither selectors nor layout,
settings, document scope, filters, or helper mixins. The fragment uses plain Less
variable syntax; compatibility is compiler-tested with locked Less 4.9.1. Native
Stylus compatibility is checked structurally and with Stylus's Less preprocessing
options, not a claimed minimum extension version or automated browser harness.

## Chezmoi example (optional consumer, never a producer dependency)

Copy the verified `data/consumer.json` to your own `.chezmoidata/achroma.json`.
Chezmoi merges JSON object keys into its data namespace; the filename does not
add a namespace. Render `fixtures/consumer/chezmoi.json.tmpl` in that source tree.
It consumes `.mappings.stylus.dark`, preserves flavor defaults, and explicitly
replaces only `accentColor` with `blue`. This emits variable values, not a native
browser backup. A downstream adapter may instead wrap the aggregate under its
own namespace; that adapter is not part of this contract.

## Deferred installer constraints

Future native references must not activate until verified installation succeeds;
retain usable app-facing paths on failed updates. The Stylus pilot uses candidate
regular files and does not activate them. Future offline rollback should restore
the previous **committed pin/snapshot** and reuse its verified installed release,
even with networking disabled and disposable cache absent. Merely retaining an
extracted release does not provide an archive for regenerating a snapshot. These
are follow-up installer tests, not claims of implemented installation behavior.
