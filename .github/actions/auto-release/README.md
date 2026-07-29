# auto-release

Cut a release for a CRT C library (aws-c-s3, aws-c-io, ...) with the version
number computed automatically instead of chosen by hand. Manually triggered
only (`workflow_dispatch`) -- there is no per-merge automation.

## What it does

1. **Resolve the previous release tag** via `git describe --tags --abbrev=0`.
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
4. **Write, commit, tag, and publish** -- overwrites the version file, commits
   it, pushes, tags `v<version>`, and creates the GitHub Release with notes
   generated from the PRs merged since the previous tag. Skipped entirely if
   step 3 decided there was nothing to release.

Every case above explains itself in the run's job summary.

## Consumer requirements

Same as `check-abi` (this action calls it internally):

- **Configure AWS credentials** with ECR pull access, so the ABI check's
  docker image can be pulled.
- **Checkout with `fetch-depth: 0`** so tag history is available.
- **Grant `contents: write`** so this action can commit, tag, push, and create
  the release.

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
      contents: write      # to commit VERSION, tag, and publish
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
| `builder-version` | no | `v0.9.93` | Builder version/channel; also the ABI docker image tag. |
| `dry-run` | no | `false` | Compute and summarize the bump/version but write/commit/tag/publish nothing. |
| `github-token` | no | `github.token` | Token used to read PR labels, commit, tag, push, and create the release. |

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
