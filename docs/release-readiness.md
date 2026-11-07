# 0.1.0 release readiness

The operator selected **0.1.0**, confirmed visual acceptance of the prepared
browser candidate, explicitly accepted self-review, and authorized publication
**after final CI and artifact checks**. No automated check below may be skipped.
See the [release body](releases/0.1.0.md) and [runbook](release.md).

## Completed source and browser evidence

- [PR #1](https://github.com/noidilin/achroma/pull/1) merged the independently
  reviewed extraction, strict verifier, CI and default coefficient lock.
- [Merged-source CI 42379529378](https://github.com/noidilin/achroma/actions/runs/42379529378)
  passed at `09b67d712135f3b37677cad68a1ea7918d7ed606`: hosted Ubuntu 24.04 x64,
  Python 3.13.13 / Node 22.17.1, 60 Python tests, 132 styles × 2 flavor paths /
  310 document sections, network-isolated generation, verification, consumer
  example and reproducibility. This is not proof of a different final tag SHA.
- [Preparation CI 42379877171](https://github.com/noidilin/achroma/actions/runs/42379877171)
  passed on `9b015dfaf7ab7279c8a0ef72c34cc9f1a24563ba`. Its hosted
  `checked-candidate` was downloaded; transfer list, archive checksum, all 15
  payload artifacts and SOURCE.json identity were independently verified.
- The operator confirmed testing the import extracted from that exact candidate,
  reporting that everything looked good, then authorized publication after checks.
  Native hashes to retain across the final branch/tag builds:
  - `import.json`: `84cb4b1cfba2cb41076c8e2984cd254feded67b36a26b982e2e40db7ae7615b1`
  - `lib.less`: `8e0bd1e98e92c7560f175132838d58e2103065514997f281a8916e3b93274717`
- OS/browser/Stylus versions, detailed per-site coverage, reimport/settings effects,
  excluded-style retention, global update-policy behavior and backup restoration
  were not individually reported. They remain unverified, not inferred passes.
  The operator accepted publication with these limitations recorded in the notes.
- Earlier reviewed dirty-tree archives are historical evidence only. Final release
  metadata must identify its own exact committed revision and actual version.

## Audited protections

The operator authorized the following settings, applied and read back via REST:

- `main-required-ci` (26759160): active on main; PR required, zero minimum peer
  approvals for a single-maintainer repository, conversations resolved; GitHub
  Actions `check` (integration 15368) required with strict up-to-date policy;
  no deletion, no force-push, no bypass actors.
- `release-tags-owner-creation` (26759161): active on `refs/tags/v*`; only
  `noidilin` (user 40153468) can bypass the creation restriction.
- `release-tags-immutable` (26759162): updates/deletion blocked for `refs/tags/v*`,
  with no bypass actors. Owner creation permission does not bypass this rule.
- Environment `release`: required reviewer `noidilin`, admin bypass disabled,
  custom deployment policy 65854149 allows tag `v*` only (not branches).
  **Self-review is allowed by explicit operator decision**; no second collaborator
  is required under this policy. Required approval is not removed.
- Default workflow token permissions remain read-only; PR approval capability is
  disabled. Workflow action revisions are pinned. Repository-wide action policy
  was not changed; avoid disrupting the independent legacy Pages workflow.
- Pages remains legacy `main` / `/`; hosted `lib/lib.less` is unchanged.
- `RELEASE_PUBLICATION_ENABLED` was absent during preparation. It may now be
  enabled only for the authorized checked release and disabled again afterward.

API read-back verifies configuration, not a completed deployment approval. Before
approving the publish job, re-read the settings and verify tag-build evidence.
No separate claims about adversarial live enforcement tests are made.

## Remaining execution gates

1. Commit finalized notes and this policy/acceptance record; obtain successful CI
   on the branch and exact final main commit after PR #2 is merged. Preserve the
   full SHA, run URL, artifact identity and downloaded verification evidence.
2. Verify its native hashes match the browser-tested candidate. Branch CI still
   uses `0.1.0-dev`; actual-version validation occurs in the tag build.
3. From the clean reviewed final commit, create and push immutable `v0.1.0` only
   after the preceding checks pass. Never move the tag to repair a failure.
4. Wait for tag-build isolation, all tests/compiler checks and actual-version
   reproducibility. Download its exact immutable artifact, verify transfer/ZIP
   checksums, manifest source/input identity, SOURCE.json, committed release notes
   and browser-tested native hashes before approving environment `release`.
5. Publish only those verified bytes, without rebuilding/clobbering. Independently
   download the public ZIP, SHA256SUMS and SOURCE.json; verify the same identity
   and hashes. Keep release/run/hash evidence and disable publication afterward.

Corrections require a new reviewed version, not a moved tag or overwritten release.
No workflow imports browser state or changes chezmoi. Windows runtime coverage,
installers, other application migrations, archive size limits and action-runtime
upgrades remain deferred, as documented in the release notes.
