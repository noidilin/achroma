# CI and first-release runbook

This phase prepares CI/release automation, not a release. It does not stage,
commit, tag, push, publish, change repository settings, replace the legacy hosted
library, install themes, or integrate chezmoi. The currently uncommitted source and
its recorded input hashes are valid **local evidence, not releasable provenance**.
Independent review and the operator gates below remain required.

## Workflow contract

- `ci.yml`: pull requests and branch pushes, `contents: read`, no secrets or
  privileged PR trigger. PRs validate the actual checked-out merge commit.
- `release.yml`: only pushed `v*` tags; nonsemantic tags fail. `v0.1.0` maps to
  producer `0.1.0`; `v0.1.0-rc.1` maps to `0.1.0-rc.1`. No build metadata or leading
  zero numeric identifiers. There is no separate producer version file: the tag
  must satisfy the shared producer version validator and have committed nonempty
  `docs/releases/<version>.md` notes. Annotated/lightweight tags both peel to the
  actual checkout commit. Checkout uses the event SHA, not a mutable branch tip;
  the local tag must peel to that checkout. A moved/deleted remote tag fails again
  before publication.
- Both use Python **3.13.13**, Node **22.17.1**, Ubuntu **24.04**, and immutable action
  SHAs listed below. The hosted OS image and bundled GitHub CLI are not immutable
  toolchain images; remote execution is still required to confirm availability.
- Online setup downloads the pinned runtimes and runs only locked `npm ci` with
  `--ignore-scripts --no-audit --no-fund` and an explicit checkout-local cache.
  No upstream refresh or package installation occurs in the validation phase.
- `tools/ci.sh` enters a new Linux network namespace using `sudo unshare --net`,
  drops to the runner UID/GID with `setpriv`, then runs `tools/ci.py check`.
  Only loopback may exist; inability to establish isolation fails the job.
  This boundary covers tests, generation, compiler subprocesses, verification,
  consumer example, and reproducibility builds. Local `tools/check.py` alone has
  audit/connection guards, **not** full process network isolation.
- Required checks fail closed: palette/schema and malformed-archive regressions,
  native fidelity, forbidden personal/path data, frozen legacy hash, all relocated
  tests, real compilation (132 styles × 2 paths / 310 document sections), plain
  Python consumer, and isolated checkout/HOME/XDG/cache reproducibility. In addition
  to fixture-version tests, CI reproduces the actual requested version/revision
  byte-for-byte in another checkout. No `continue-on-error` gates.
- Clean tracked/untracked source is required before and after validation; ignored
  scratch/dependency directories are allowed. Manifest input hashes are compared
  against the checkout before handoff. `SOURCE.json` records the full checked-out
  revision and optional tag; ZIP provenance has that same revision.
- Verified ZIP/checksum, source identity, and committed notes are uploaded once.
  The publish job downloads **only the build job's immutable artifact ID in the
  same run**, verifies the transferred checksum-list SHA-256 from the build job's
  outputs, then every listed file and the archive checksum. No rebuilding occurs.
  Artifact retention is 14 days; an expired artifact requires a fresh checked run
  and approval, not substitution with an artifact name from another run.
- Only `publish` has `contents: write`, and its token is exposed only to the final
  publication step. It is disabled unless repository variable
  `RELEASE_PUBLICATION_ENABLED` equals `true`, then waits on environment `release`.
  Existing releases are refused; `gh release create` has no overwrite/clobber path.
  Semver prereleases use GitHub's prerelease flag. No Pages actions or settings
  changes are included; Pages remains branch `main`, root `/`, and `lib/lib.less`
  remains byte-for-byte frozen.

### Official action pins and documentation

Pins were resolved read-only with `git ls-remote` against these official repos
(the tag refs below pointed directly to these commits). Local evidence is in
`.work/ci-preparation/action-pins.log`:

| Official repository/tag | Immutable commit |
| --- | --- |
| [actions/checkout v4.2.2](https://github.com/actions/checkout/tree/v4.2.2) | `11bd71901bbe5b1630ceea73d27597364c9af683` |
| [actions/setup-python v5.6.0](https://github.com/actions/setup-python/tree/v5.6.0) | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| [actions/setup-node v4.4.0](https://github.com/actions/setup-node/tree/v4.4.0) | `49933ea5288caeca8642d1e84afbd3f7d6820020` |
| [actions/upload-artifact v4.6.2](https://github.com/actions/upload-artifact/tree/v4.6.2) | `ea165f8d65b6e75b540449e92b4886f43607fa02` |
| [actions/download-artifact v4.3.0](https://github.com/actions/download-artifact/tree/v4.3.0) | `d3f86a106a0bac45b974a628896c90dbdf5c8093` |

Official [upload inputs/outputs](https://github.com/actions/upload-artifact/blob/ea165f8d65b6e75b540449e92b4886f43607fa02/action.yml)
and [download inputs](https://github.com/actions/download-artifact/blob/d3f86a106a0bac45b974a628896c90dbdf5c8093/action.yml)
were fetched to `.work/ci-preparation/`: the uploader supplies `artifact-id`, and
`artifact-ids` downloads that identity (not a mutable name). GitHub's built-in
artifact digest checks are not the sole publication integrity gate.
See also [environment protection](https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment)
and [CLI release creation](https://cli.github.com/manual/gh_release_create).
Local actionlint is syntax/static validation, **not remote Actions execution**.

## Operator prerequisites — before enabling publication

1. Review and approve all extracted source **including untracked files**, fixtures,
   provenance/licenses, workflows, and this runbook. Review `git status --short
   --untracked-files=all`, not only `git diff` (most pilot files start untracked).
   Stage only explicitly approved paths, inspect the staged diff, and commit the
   complete approved tree. Preserve the original `.work/review-fixed` evidence.
   Do not include caches, node_modules, personal files, or dotfiles changes.
2. Configure repository Actions policy to permit only reviewed pinned actions;
   select read-only default token permissions and required PR CI checks. Protect
   release tags from unauthorized creation, movement, or deletion. Confirm the
   existing Pages source is still `main` / `/`; do not deploy Pages here.
3. **Create environment `release` with required trusted reviewers**, prevent
   self-review, restrict deployment tags to reviewed `v*` tags, and disable bypass
   where available. Confirm repository visibility/plan actually supports and
   enforces these protection rules. An environment name can be auto-created with
   **no** protection; neither that name nor a repository variable guarantees human
   review. If reviewer enforcement is unavailable, keep publication disabled.
4. Keep `RELEASE_PUBLICATION_ENABLED` absent/false until environment protection and
   repository permissions have been audited. Only the operator may set it to `true`
   after those prerequisites and remote CI/browser review below. No secrets are
   required: publication uses the scoped GitHub token, never a privileged PR token.

## First-release sequence (operator only)

1. Choose the semantic version (for example `0.1.0` or an explicitly reviewed
   prerelease). Commit `docs/releases/<version>.md` with changelog/release notes:
   scope (palette + Stylus only), schema/path/version policy, color/upstream changes
   or explicit absence thereof, licenses, global update-policy caveat, manual
   acceptance evidence, supported/tested platforms, and deferred limitations.
   This file is the exact published release body, not auto-generated mutable notes.
2. Confirm all approved source and notes are committed and the tree is clean:
   `git status --porcelain --untracked-files=all` must be empty (ignored scratch is
   fine). Record `git rev-parse HEAD`. The earlier baseline HEAD and uncommitted
   manifest hashes are not substitutes for this complete source commit.
3. Through the operator's normal reviewed push/PR process, obtain **successful remote
   CI on the exact intended commit**. Retain run URL, full source SHA, checks,
   candidate artifact ID/digest, and independent download/verification evidence.
   Inspect `SOURCE.json` and `manifest.json`; verify archive/checksum using
   `tools/verify.py`. A PR merge-SHA check alone is not proof of a different final
   commit; require its branch-push CI too. Local success/actionlint do not satisfy
   this gate. Inspect Linux namespace setup logs; do not weaken isolation if it fails.
4. Complete independent manual browser acceptance of that candidate in an isolated
   profile: export a live backup first; import 132 styles, test dark/light and
   preserved Frappé/Macchiato paths, chosen accent/settings and representative
   document scopes, reimport behavior, excluded-style retention, global
   `updateInterval = 0` effect on unrelated styles, and backup restore/rollback.
   Record browser/Stylus versions and what was/was not visually tested. Compiler
   success is not visual or real import acceptance. No command here imports state.
5. After review/setup, enable the repository variable. From the clean intended
   commit, the operator may create and push an immutable `v<version>` tag pointing
   to exactly that SHA. Do not move a tag to repair failures. These are future
   operator actions, **not actions performed by this preparation task**.
6. Wait for the tag build to pass the same offline checks and actual-version
   reproducibility. Before approving environment `release`, independently inspect
   its source revision, notes, artifact ID/checksums and ZIP; reconcile them to the
   reviewed commit/CI proof and manual acceptance. Deny approval on any mismatch.
   If publication is disabled, `publish` is skipped; enabling the variable later
   requires a deliberate rerun, successful checks, and approval.
7. After approval/publication, independently download `achroma-<version>.zip`,
   `SHA256SUMS`, and `SOURCE.json`; verify checksum/manifest/native identity and
   retain release URL/run URL/hash evidence. Checksums prove integrity, not an
   independent authenticity source. Never silently overwrite an existing release;
   use a newly reviewed version/tag for corrections. Disable the publication
   variable again if desired. Dotfiles/chezmoi integration is a separate phase and
   must wait for a trusted downloadable release.

## Archive contract

`achroma-<version>.zip` contains only regular files:

- `manifest.json`
- `palette/{dark,light}.json`
- `mappings/stylus/{dark,light}.json`
- `themes/stylus/{import.json,lib.less}`
- `fragments/stylus/{dark,light}.less`
- `data/consumer.json`
- `reports/stylus-build.json`
- `licenses/*`

No unimplemented applications are advertised. ZIP members are sorted, with fixed
1980 metadata, mode 100644, no symlinks, no timestamps/absolute paths in payload
provenance, and no compression-library variability (`ZIP_STORED`). Separate
`SHA256SUMS` hashes the archive. The manifest hashes every payload file except
itself; the external checksum covers the manifest too. Neither checksum file nor
archive URL/checksum is embedded in the payload. Workflow artifact transport
metadata need not be reproducible; the contained ZIP is.

Manifest v1 has exactly `schemaVersion`, `release`, `applications`, `buildInputs`,
and `artifacts`. `release` matches the consumer aggregate's `version` and
`sourceRevision`; input/artifact maps use relative POSIX paths and SHA-256 values.
`applications.stylus` records native format, compatibility caveat, all preserved
native names, style count, and variant/flavor identity. Build inputs record
canonical palettes, mapping, producer code, schemas, vendor snapshots/lock, and
license notices. Upstream URLs in lock/report are provenance, not downloaded or
mutable build inputs. Supplied revision must be a full SHA; local uncommitted
candidate inputs are identified by hashes but cannot pass the CI clean-tree gate.

`tools/verify.py` uses focused shared stdlib contract checks, not a general JSON
Schema engine. It validates exact palette/mapping keys, types, colors/defaults,
release identity, and manifest application/count/name/input metadata in addition
to archive checksum, safe regular member names, payload hashes, and aggregate
identity. Report native hashes must have exactly both expected entries. Parsed
native names/count, global update policy and effective saved variable defaults
must agree with manifest/report/mappings. Unknown JSON fields are rejected at
contract boundaries; duplicate JSON keys are rejected too. Original upstream
select options/default metadata are preserved, including the native `subtext0`
accent option (the configurable producer default remains a chromatic role).

Verification does not extract files and is not an installer or trust bootstrap.
Archive/member size limits are not implemented; use reviewed local artifacts,
not this verifier as a resource-isolation boundary. Review trusted release
provenance independently before distributing.

Before 1.0, incompatible schemas/paths require a minor release; after 1.0, a major.
Call out color or upstream style changes in release notes. Frozen extraction
fixtures intentionally detect such changes. For accent customization, use the
[source recipe](stylus.md), build a distinct local candidate, and never replace
verified public release bytes with a customized rebuild.
