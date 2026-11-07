# Prospective 0.1.0 release readiness

**Not release approval. No public release exists; 0.1.0 is prospective.**
This checkpoint supplements the historical [validation log](validation.md) and
[first-release runbook](release.md); older pending-hosted-CI statements describe
those earlier checkpoints, not the merged-source result below. The proposed
[release body](releases/0.1.0.md) still requires review and final-commit evidence.

## Completed merged-source evidence

[PR #1](https://github.com/noidilin/achroma/pull/1) was merged with explicit user
proceed authorization. The clean `main` baseline for this documentation task was
`09b67d712135f3b37677cad68a1ea7918d7ed606`.

Read-only `gh run view` metadata and logs confirm:

- [Run 42379529378](https://github.com/noidilin/achroma/actions/runs/42379529378),
  event `push`, head SHA `09b67d712135f3b37677cad68a1ea7918d7ed606`, conclusion
  **success**; [check job](https://github.com/noidilin/achroma/actions/runs/42379529378/job/128424019508)
  succeeded through artifact upload.
- Ubuntu 24.04 x64, Python **3.13.13**, Node **22.17.1**; locked npm preparation
  preceded `bash tools/ci.sh` network-namespace validation. Namespace enforcement
  is fail-closed (`sudo unshare --net`, privileges dropped, only loopback allowed).
- **60 Python tests** (22 relocated + 38 contract/CI/filter-lock),
  **132 UserCSS styles × 2 flavor paths / 310 document sections**, helper fixtures,
  verification of **15 payload artifacts**, and plain Python consumer passed.
  Isolated fixture and actual requested-version/revision builds reproduced.
- Requested candidate version was **0.1.0-dev**, not 0.1.0. Log-reported actual
  merged-revision ZIP SHA-256:
  `5aa6f1238719d5d6bf6693e623ff38c9b801b8feee1f92a7c55c6ae2aefb820b`.
  Log-reported `TRANSFER.sha256` SHA-256:
  `185472c9a7e8953b3a07336b57e951774ddcdb3d74fcb3c27613d98ee45ac01b`.
- GitHub artifact API identifies `checked-candidate`, ID **13576644470**, digest
  `sha256:e23662b7878052ae07afbb7aa81624fe5fd61c2f920dffac1ed769beee9067f1`,
  tied to that run and SHA; not expired at inspection. Workflow retention is
  **14 days**. The transport artifact digest is not the inner release ZIP hash.
  This documentation task inspected metadata/logs, not an independent download of
  this merged-run artifact.

Earlier branch evidence remains separate:
[run 42377168864](https://github.com/noidilin/achroma/actions/runs/42377168864)
succeeded at `d1ec618320bf4b5e31eaf4cc64f2cff02fec1ec0`. The prior operator checkpoint
records independent hosted artifact download, transfer/checksum verification and
`SOURCE.json` matching that exact revision. That proof is **not** a download check
of the merged-run artifact or the future final release artifact.

## Current publication posture

The parent's read-only repository audit reported:

- Pages remains legacy branch `main`, path `/`, unchanged.
- Default workflow token permissions are read-only; workflows cannot approve PRs.
- Repository Actions variables are empty: `RELEASE_PUBLICATION_ENABLED` is absent,
  so the publication job is disabled.
- Only environment `github-pages` exists; there is **no `release` environment**.
- Repository rulesets list is empty. Release-environment required reviewers,
  self-review prevention, deployment restrictions to `v*` tags and release-tag
  protections are **not established**.

These observations are not guarantees of future state or protection availability.
An environment name alone is not an approval gate. Visibility/plan enforcement
must be confirmed before publication; keep publication disabled if required
reviewer enforcement is unavailable. No settings were changed by this task.

## Remaining operator decisions and gates

- [ ] Review the proposed scope/body and confirm **0.1.0** versus a separately
  reviewed prerelease. Commit only approved source and notes through the normal
  reviewed process; record the final clean intended tag SHA.
- [ ] Obtain successful remote branch-push CI on **that exact notes-bearing final
  commit**. These new documents change the intended tag SHA; merged-source CI
  above cannot satisfy this final-commit gate. A different PR merge SHA is not a
  substitute either.
- [ ] Retain final run URL, full SHA, artifact ID/digest, version and independent
  download evidence. Verify transfer list, ZIP checksum, `manifest.json` inputs
  and `SOURCE.json` identity using the runbook. If artifacts expire, obtain a
  fresh checked run; do not substitute another run's artifact. Branch CI uses
  0.1.0-dev; the later tag build must separately check actual 0.1.0 bytes.
- [ ] **Browser acceptance PENDING:** choose and record browser/OS/Stylus versions
  and candidate identity. Export a live backup, then test in an isolated profile:
  import/count 132 styles; enabled states/inclusions/site settings; dark/light
  transitions; preserved Frappé/Macchiato; chosen accent; representative document
  scopes and text/dashboard/SVG/filter/syntax/focus/hover/selection/contrast cases;
  reimport; retention of excluded Codeberg/PythonAnywhere; global
  `updateInterval = 0` effect on unrelated styles; backup restore and rollback.
  Record untested visual cases too. Earlier user confirmation does not cover this
  full new checklist. Main-profile import requires separate approval.
- [ ] Decide/configure and audit allowed pinned actions, required CI checks,
  release-tag creation/movement/deletion protections and an enforced `release`
  environment: trusted required reviewers, prevention of self-review, reviewed
  `v*` deployment tags and bypass restrictions where available. Confirm actual
  repository visibility/plan enforcement; do not infer it from API names.
- [ ] Only after the preceding gates, decide whether to enable
  `RELEASE_PUBLICATION_ENABLED=true` and authorize immutable `v0.1.0` creation at
  the reviewed final SHA. This preparation creates no tag and authorizes none.
- [ ] Require successful tag-build isolation, actual-version reproducibility and
  committed-note identity. Independently reconcile that run's artifact and
  checksums to the reviewed SHA and browser-tested candidate before environment
  approval. Publish only those verified bytes; no rebuild or overwrite.
- [ ] After any separately authorized publication, independently download/verify
  release assets and retain release/run/hash evidence. Corrections require a new
  reviewed version, not a moved tag or overwritten release.

Action Node20 deprecation/API warnings were nonblocking in the successful merged
run; reviewed action upgrades remain deferred. Windows/browser execution,
installers, other app integrations and archive size limits remain outside this
bounded documentation task. No tests were rerun, live state imported, system tools
installed, or source/fixtures/workflows/dotfiles edited here. Only the preparation
branch and these two unstaged documentation files were created; no commit, push,
tag, PR, release or settings mutation was performed.
