# Scheduled upstream proposals

`.github/workflows/upstream-refresh.yml` runs Mondays at **06:23 UTC** and supports
manual dispatch from `main`. GitHub schedules can be delayed or disabled for
inactivity; this is not a freshness SLA. Merge this workflow into the default
branch before expecting schedules to exist. It is restricted to `noidilin/achroma`
and `refs/heads/main`; it has no PR, workflow-run, tag, release or Pages trigger.

## Strategy and trust boundary

- Resolve `catppuccin/userstyles`' official default-branch HEAD through GitHub's
  commits API, validate the full SHA, then call the existing Stylus updater.
  Always download **all** endpoints, even if the standard-library SHA is unchanged.
  Export and syntax CSS are independent snapshots; lock URLs and SHA-256 values
  record their provenance, not a fictitious shared revision.
- Ordinary CI, release and generation remain offline. The refresh job alone has
  online upstream access. Its token is read-only and is not passed to the updater.
  Locked npm preparation precedes network-isolated validation with privileges
  dropped, using the same Python/Node versions as CI.
- Stage a synthetic local commit of the snapshot changes. Independently attempt
  build, archive verification, complete compiler checks, and full existing CI.
  Record every exit code, including failures, in `proposal.json` and run logs.
  Infrastructure/setup/namespace failures stop the workflow; completed validation
  failures may still produce a **draft**, explicitly failing proposal. Exit 125
  means not run. Synthetic local commit identity is not the eventual PR SHA.
- A separate job downloads **only this run's immutable artifact ID**. Its checkout
  is the original trusted event SHA, never the proposal branch or artifact code.
  Only its final step receives `GITHUB_TOKEN`, scoped to `contents: write` and
  `pull-requests: write`. It parses candidate data, checks exact regular-file
  allowlists, hashes, revision shapes, expected URLs and unchanged LICENSE bytes.
  It executes no downloaded files, Less, npm scripts, PR scripts or shell data.
  No PR helper action, App credential or repository secret is introduced. All
  action pins reuse official pins, reverified through official tag refs.
- Only the eight files under `applications/stylus/vendor/` may enter a commit:
  `export.json`, `std.less`, `LICENSE`, four syntax CSS snapshots, and
  `upstream.lock.json`. `proposal.json` is evidence, not source. Palettes,
  `filters.lock.json`, fixtures, notices, scripts and frozen `lib/lib.less` cannot
  be changed by the publisher. LICENSE is allowed in the file set but must remain
  byte-identical; changed license text fails closed before staging/publication.
- One branch, `automation/catppuccin-refresh`, and one open draft PR are reused.
  Identical branch trees create no new commit; no difference from main means no
  remote calls or PR. Metadata/log links may be refreshed on rerun. All runs share
  one non-cancelling concurrency group. Main movement requires a fresh run. The
  branch is rebuilt from the audited main base, so only this dedicated automation
  branch may be force-updated; main is never pushed. An observed branch change,
  unrecognized author/message, or out-of-scope diff stops publication. API ref
  updates are not atomic compare-and-swap against concurrent human edits: reserve
  this branch for the bot and stop scheduled runs before manually changing it.
  Human commits are not knowingly overwritten.
- Closing a proposal without merging pauses further proposals until an operator
  reopens it. A PR-creation permission failure is explicit; the branch may already
  exist, and a retry reuses it. No alternate identity or token fallback exists.
  A no-op run leaves any existing PR untouched; review/close stale proposals manually.

## Repository permissions and required CI

Initial read-back during implementation confirmed:

- `default_workflow_permissions: read`;
- `can_approve_pull_request_reviews: false` (the repository's combined Actions
  create/approve-PR setting);
- main ruleset `26759160` active, no bypass, strict required Actions `check`, PR
  required, no force-push/deletion;
- release approval still required, self-review allowed, admin bypass disabled;
- `RELEASE_PUBLICATION_ENABLED=false`.

The operator subsequently authorized enabling “Allow GitHub Actions to create and
approve pull requests.” The setting was updated and read back as
`can_approve_pull_request_reviews: true`, with `default_workflow_permissions: read`
unchanged. This repository setting combines creation and approval; the workflow
only creates PRs and never calls an approval endpoint. Publication remains disabled
(`RELEASE_PUBLICATION_ENABLED=false`). A 403 is a failed publication, not a
successful PR; there is no alternate-credential fallback. If this broader setting
is later disabled, use manual proposals; introducing an App credential needs new
approval.

`GITHUB_TOKEN`-created pushes/PRs do **not** trigger ordinary follow-on workflows.
The proposal's explicit checks are evidence, **not** the required PR `check` and
not an assertion that PR CI ran. After inspecting the draft, a maintainer can
close/reopen it using their own normal GitHub identity, or push a reviewed change
to trigger ordinary CI. Reopening must be an operator action, not another bot
API call. Obtain successful required CI on the exact final candidate/merge base;
new scheduled updates invalidate earlier evidence. Do not bypass main protections
or enable auto-merge. No check status is synthesized by this workflow.

## Maintainer promotion path

1. Inspect the draft diff, exact upstream SHA, independent checksums and run logs.
   Review style additions/deletions, selectors, settings, imports and exclusions.
   Any unsupported dependency/download failure stops refresh; investigate rather
   than adding automatic exclusions or arbitrary URLs.
2. Review syntax CSS licensing and `licenses/provenance.json` against the actual
   fetched bytes. Unchanged Userstyles LICENSE does **not** prove CSS licensing or
   supplementary notice provenance. Automation neither updates notices nor claims
   their old source revisions describe new CSS. If upstream LICENSE changes,
   perform a manual refresh and reviewed license/provenance update instead.
3. If extraction hashes, native outputs or style-count baselines fail, inspect and
   explain each intended difference. Stop scheduled runs before editing the bot
   branch, or use a separate maintainer branch/PR and close the bot proposal.
   Update narrowly justified fixtures/count assertions/notices only after review;
   never regenerate all baselines to make a PR green. Filters/palettes remain
   separate approved inputs; use the explicit filter-lock process in `stylus.md`
   only for a separately authorized palette change.
4. Build, verify, and compile every supported style/flavor. Complete isolated
   browser acceptance and preserve a live backup before any manual import, per
   `stylus.md`. Record new upstream/native behavior and licensing changes.
5. Trigger ordinary CI through the maintainer action above, verify green required
   checks on the final candidate, then manually mark ready and merge after review.
   A refresh merge is not release authorization. The separate release runbook,
   environment approval, immutable tag controls and disabled publication variable
   still apply. No automatic merge, tagging, approval, publication or deployment
   is added here.

## Local validation versus hosted execution

Tests mock all downloads and GitHub writes. `tests/test_upstream.py` covers no-op,
independent CSS changes at unchanged SHA, bad revisions/download failures, data
handoff restrictions, draft PR creation/update/idempotency, declined PRs, human
edits/main movement, permission failures/retry, validation failure recording, and
static workflow privilege seams. Actionlint checks workflow syntax. None of these
is evidence of hosted scheduling, token permissions, branch protection enforcement,
namespace availability, or actual PR creation. After review/merge and explicit
permission approval, manually dispatch on main and inspect the run and draft PR
before relying on future schedules. No hosted refresh run was triggered during
implementation.

Local implementation evidence (macOS, Python 3.13.13 / Node 22.17.1):

```sh
python3 -I -B tools/check.py --output .work/scheduled-refresh-final \
  --cache .work/scheduled-refresh-cache --version 0.1.0-dev \
  --source-revision eb4693f91e2d93e146f660b3dc5a1d2981267e15
actionlint .github/workflows/ci.yml .github/workflows/release.yml \
  .github/workflows/upstream-refresh.yml
git diff --check
```

All **72 Python tests** passed (22 Stylus, 50 root, including 12 new proposal tests),
plus archive verification, isolated reproducibility tests, 132 styles × 2 flavor
paths / 310 document sections, and the consumer example. Log:
`.work/scheduled-refresh-final.log`. Existing native fixtures passed unchanged.
An earlier rerun reused a populated output directory and was refused
by the producer; the final successful run used the fresh output path above.
The supplied revision identifies the existing base; this dirty-tree validation is
local evidence, not a release or hosted exact-commit CI receipt. No upstream
snapshot refresh or credential introduction was performed locally. The subsequent
operator-authorized PR-permission update is recorded above; branch publication
is separate from these local test results.
