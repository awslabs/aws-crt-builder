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
4. **Write, push, tag, and publish** -- overwrites the version file, commits
   it, and pushes straight to the default branch over SSH using a deploy key
   fetched fresh from AWS Secrets Manager (see `deploy-key-secret-id` below),
   then tags the new commit and creates the GitHub Release with notes
   generated from the PRs merged since the previous tag. Skipped entirely if
   step 3 decided there was nothing to release.

Every case above explains itself in the run's job summary.

## Consumer requirements

Same as `check-abi` (this action calls it internally):

- **Configure AWS credentials** with ECR pull access and Secrets Manager read
  access (`secretsmanager:GetSecretValue` on `deploy-key-secret-id`), so both
  the ABI check's docker image can be pulled and the deploy key retrieved.
- **Checkout with `fetch-depth: 0`** so tag history is available.
- **Grant `contents: write`** so this action can create the release.
- **Register a deploy key with write access** on the repo (Settings -> Deploy
  keys), and store its private half in AWS Secrets Manager at
  `deploy-key-secret-id`. This is what actually authorizes the push to the
  default branch -- the job's own `github.token` never touches it, avoiding a
  standing broad-scope PAT (same approach as aws-crt-swift's
  `update-version.yml`: a repo-scoped key fetched fresh each run, not a
  long-lived secret sitting in a user/bot account).

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
      id-token: write      # for configure-aws-credentials OIDC
      contents: write      # to create the release
      pull-requests: read  # to scan merged PRs for the minor label
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
```

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `lib-name` | yes | — | Library name; maps to `lib<name>.so` for the ABI check. |
| `version-file` | no | `VERSION` | Path to the file holding `major.minor.patch`. |
| `minor-pr-label` | no | `minor` | PR label that forces a minor bump when the ABI is compatible. |
| `builder-version` | no | `latest` | Builder version/channel; also the ABI docker image tag. `latest` tracks the most recent published builder release. |
| `dry-run` | no | `false` | Compute and summarize the bump/version but write/commit/tag/publish nothing. |
| `github-token` | no | `github.token` | Token used to read PR labels and create the release. |
| `deploy-key-secret-id` | no | `aws-crt-bot/deploy-key/privatekey` | AWS Secrets Manager secret ID holding the private half of the deploy key used to push the version-bump commit and tag. |

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
    └── cut-release.sh                # deploy key -> write VERSION, commit, push, tag, gh release create
```
