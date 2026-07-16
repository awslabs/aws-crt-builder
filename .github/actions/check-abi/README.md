# check-abi

Dump and compare the ABI of a CRT C shared library between a pull request's head
and its base ref, and **label the PR** with the implied semver bump (`patch` if
the ABI is backward-compatible, `minor` if it changed). This is intended for use
with the CRT C libraries (ex: aws-c-s3, aws-c-io).

This check is informational: a compatible or incompatible ABI both **succeed**
and are surfaced as a label. The job fails **only** when abidiff could not
produce a verdict (a tool/usage error), because then there is no trustworthy
result to label with.

## What it does

The ABI toolchain (libabigail's `abidw`/`abidiff`, `cmake`, `g++`) is **baked
into a docker image** (`aws-crt-ubuntu-22-abi-x64`) instead of being installed
on every CI run. The action pulls that image and runs the whole check inside
it:

1. **Pull ABI image** — `docker login` to ECR and pull
   `aws-crt-ubuntu-22-abi-x64:<builder-version>`.
2. **Run ABI check in container** — one `docker run` executes all of:
   1. **Download builder** — `builder.pyz`; building is the only part that needs
      builder, because builder owns the CRT dependency graph.
   2. **Build base and head refs** in parallel — both as shared libs with debug info.
   3. **Dump ABI for base and head** in parallel — `abidw --headers-dir <install>/include`,
      scoped to public headers.
   4. **Run abidiff** on the two ABI dumps (diffing dumps, not the raw `.so`s,
      catches struct-layout changes a direct `.so`-to-`.so` abidiff can miss).
   5. **Publish report** — appends the verdict and the abidiff text output to the job summary.
   6. **Choose the label** — `patch` (no change / compatible change), `minor`
      (incompatible change), or fail (tool/usage error — abidiff exit bit 0 or 1 set).
      The chosen label is written to a host-mounted file so it escapes the container.
3. **Label PR** — on the host (which has the PR context and token), add the
   chosen label and remove the opposite one via `gh pr edit`.

The in-container stages run as a single process because they chain state through
`$GITHUB_ENV`, which does not survive across a `docker run` boundary
(`scripts/abi_check.sh` is the orchestrator that bridges it). Labeling runs on
the host because the container has neither the PR number nor a GitHub token.

## Consumer requirements

The consumer workflow must, before invoking this action:

- **Configure AWS credentials** with ECR pull access (e.g.
  `aws-actions/configure-aws-credentials`), so the image can be pulled.
- **Checkout with `fetch-depth: 0`** so the base branch history is available for
  the worktree and `git merge-base`.
- **Grant `pull-requests: write`** so the action can label the PR. Note: on PRs
  from forks GitHub forces the token read-only regardless of this setting, so
  labeling is skipped (the verdict is still in the job summary).

## Usage

Add a workflow to the library repo (see `aws-c-s3/.github/workflows/check-abi.yml`):

```yaml
jobs:
  check-abi:
    runs-on: ubuntu-24.04
    permissions:
      id-token: write        # for configure-aws-credentials OIDC
      pull-requests: write   # to label the PR patch/minor
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.CRT_CI_ROLE_ARN }}
          aws-region: us-east-1
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Check ABI
        # note: using "@main" because "@${{env.BUILDER_VERSION}}" doesn't work
        # https://github.com/actions/runner/issues/480
        uses: awslabs/aws-crt-builder/.github/actions/check-abi@main
        with:
          lib-name: aws-c-s3
```

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `lib-name` | yes | — | Library name; maps to `lib<name>.so`. |
| `builder-version` | no | `v0.9.93` | Builder version/channel used to build; also the ABI image tag. |
| `builder-source` | no | `releases` | `releases` for tags, `channels` for branch builds. |
| `builder-host` | no | CloudFront URL | Builder artifact host. |
| `image-registry` | no | CRT ECR registry | ECR registry hosting the ABI image. |
| `image-name` | no | `aws-crt-ubuntu-22-abi-x64` | ABI docker image name. |
| `github-token` | no | `github.token` | Token used to label the PR (needs `pull-requests: write`). |
| `patch-label` | no | `patch` | Label applied when the ABI is backward-compatible. |
| `minor-label` | no | `minor` | Label applied when the ABI changed. |

## The label

The check maps the abidiff bitmask exit code to a semver label:

| abidiff exit | Meaning | Result |
|-----------|---------|--------|
| bit 0/1 set (odd, or usage error) | tool error — check could not run | **job fails**, no label |
| bit 3 set (e.g. `12`) | ABI changed incompatibly | job passes, PR labeled `minor` |
| otherwise (e.g. `0`, `4`) | no change, or a compatible change | job passes, PR labeled `patch` |

See `scripts/compare.sh` for the full bit layout
(`ABIDIFF_ERROR`/`ABIDIFF_USAGE_ERROR`/`ABIDIFF_ABI_CHANGE`/`ABIDIFF_ABI_INCOMPATIBLE_CHANGE`).

The two labels are mutually exclusive: applying one removes the other, so a
re-run after a code change flips the label cleanly.

## The docker image

The image is defined at `.github/docker-images/ubuntu-22-abi-x64/Dockerfile` and
is built + pushed to ECR (tagged with the builder version) by the
`create-channel.yml` / `create-release.yml` workflows, same as every other
`aws-crt-*` image.

## Layout

```
check-abi/
├── action.yml          # pull image + docker run the orchestrator + label the PR
├── README.md
└── scripts/
    ├── abi_check.sh    # in-container orchestrator (build->dump->compare->report->gate)
    ├── build.sh        # resolve base ref, worktree, build both refs (parallel)
    ├── dump.sh         # locate both .so, abidw both (parallel)
    ├── compare.sh      # abidiff on the two dumps; record bitmask rc
    ├── report.py       # write verdict + abidiff text output to the job summary
    └── gate.sh         # map bitmask exit code -> patch/minor label; fail only on tool error
```
