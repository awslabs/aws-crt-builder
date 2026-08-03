# auto-release

Cut a release for a CRT C library (aws-c-s3, aws-c-io, ...) with the version
number computed automatically instead of chosen by hand.

A maintainer still triggers the workflow manually from the GitHub Actions UI
(`workflow_dispatch`) -- this does not release on every merge, and does not
remove the human decision of *when* to release. What it removes is manually
deciding and typing the *version number*: today that's picked by hand and
error-prone once ABI/API compatibility matters; this action derives it from
the ABI check and PR labels instead, so the bump is consistent every time.
Releasing automatically on every merge was considered and rejected -- that
would produce far more releases than any of these libraries want.

## What it does

1. **Resolve the previous release tag** -- the nearest tag whose version file
   is a plain `major.minor.patch`. A manually-cut beta/rc tag (e.g.
   `0.7.5-beta`) is skipped rather than blocking automation: it's ignored and
   the last real stable release is used instead.
2. **Check ABI** between that tag and the current ref, via
   [`check-abi`](../check-abi)'s `base-ref` override (the same action/toolchain
   PRs use for labeling, just pointed at a tag instead of a PR base).
3. **Compute the next version** (see
   [`scripts/compute-version-bump.sh`](scripts/compute-version-bump.sh) for the
   exact precedence):
   - No commits since the previous tag -> skip, no release cut.
   - ABI check returned `needs-review` (an API break -- callers fail to
     recompile) -> **fail**. Major bumps are never automated; cut that tag by
     hand.
   - ABI check returned `minor` (a binary-only break) -> minor bump, no debate.
   - Otherwise, a merged PR since the previous tag labeled `minor` -> minor
     bump.
   - Otherwise -> patch bump.
   - SOVERSION is always `major.minor` of the resulting version.
4. **Write, merge, tag, and publish** -- overwrites the version file, commits
   it to a new branch, opens a PR against the default branch, and merges it
   with admin rights (bypassing required reviews/status checks, the same way
   aws-crt-cpp's release automation does), then tags the merged commit and
   creates the GitHub Release with notes generated from the PRs merged since
   the previous tag. Skipped entirely if step 3 decided there was nothing to
   release. Merging goes through a PR rather than a direct push because the
   default branch is expected to require review -- see `merge-token` below.

Every case above explains itself in the run's job summary.

## Consumer requirements

Same as `check-abi` (this action calls it internally):

- **Configure AWS credentials** with ECR pull access, so the ABI check's
  docker image can be pulled.
- **Checkout with `fetch-depth: 0`** so tag history is available.
- **Grant `contents: write` and `pull-requests: write`** so this action can
  push the version-bump branch, open the PR, tag, and create the release.
- **Provide a `merge-token`** if the default branch requires reviews or
  status checks -- the job's own `github.token` cannot bypass those, only a
  personal access token with admin merge rights can (same reason
  aws-crt-cpp's release workflow needs a second token, `TAG_PR_TOKEN`, solely
  to merge its version-bump PR). Without one, the version-bump PR is opened
  but the merge step fails on any protected default branch.

## Usage

Add a workflow to the library repo:

```yaml
name: Release
on:
  workflow_dispatch: {}

jobs:
  release:
    runs-on: ubuntu-24.04
    permissions:
      id-token: write       # for configure-aws-credentials OIDC
      contents: write       # to push the version-bump branch, tag, and publish
      pull-requests: write  # to open the version-bump PR and scan merged PRs for the minor label
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.CRT_CI_ROLE_ARN }}
          aws-region: us-east-1
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Release
        # note: using "@main" because "@${{env.BUILDER_VERSION}}" doesn't work
        # https://github.com/actions/runner/issues/480
        uses: awslabs/aws-crt-builder/.github/actions/auto-release@main
        with:
          lib-name: aws-c-s3
          merge-token: ${{ secrets.RELEASE_MERGE_TOKEN }}
```

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `lib-name` | yes | — | Library name; maps to `lib<name>.so` for the ABI check. |
| `version-file` | no | `VERSION` | Path to the file holding `major.minor.patch`. |
| `minor-pr-label` | no | `minor` | PR label that forces a minor bump when the ABI is compatible. |
| `builder-version` | no | `latest` | Builder version/channel; also the ABI docker image tag. `latest` tracks the most recent published builder release. |
| `dry-run` | no | `false` | Compute and summarize the bump/version but write/commit/tag/publish nothing. |
| `github-token` | no | `github.token` | Token used to read PR labels, push the version-bump branch, and create the release. |
| `merge-token` | no | _(falls back to `github-token`)_ | PAT with admin merge rights on the default branch, used only to merge the version-bump PR. Required if the default branch has required reviews/status checks. |

### Outputs

| Output | Description |
|--------|-------------|
| `skip` | `"true"` if no release was cut. |
| `bump` | `"minor"` \| `"patch"`. Empty if skipped. |
| `new_version` | The released `major.minor.patch`. Empty if skipped. |
| `new_soversion` | The released `major.minor`. Empty if skipped. |

## Layout

```
auto-release/
├── action.yml                       # resolve tag -> check-abi -> compute version -> write/commit/tag/publish
├── README.md
└── scripts/
    ├── compute-version-bump.sh       # the version-bump decision + job-summary explanation
    └── cut-release.sh                # write VERSION, commit, tag, gh release create
```
