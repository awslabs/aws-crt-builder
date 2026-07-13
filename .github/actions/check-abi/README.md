# check-abi

Dump and compare the ABI of a CRT C shared library between a pull request's head
and its base ref, and fail the build on an unauthorized binary-incompatible
change. This is intended for use with the CRT C libraries (ex: aws-c-s3, aws-c-io).

## What it does

The ABI toolchain (`abi-compliance-checker`, `abi-dumper`, `universal-ctags`,
`cmake`, `g++`, `libssl-dev`) is **baked into a docker image**
(`aws-crt-ubuntu-22-abi-x64`) instead of being installed on every CI run. The
action pulls that image and runs the whole check inside it:

1. **Pull ABI image** — `docker login` to ECR and pull
   `aws-crt-ubuntu-22-abi-x64:<builder-version>`.
2. **Run ABI check in container** — one `docker run` executes all of:
   1. **Download builder** — `builder.pyz`; building is the only part that needs
      builder, because builder owns the CRT dependency graph.
   2. **Build base and head refs** in parallel — both as shared libs with debug info.
   3. **Dump ABI for base and head** in parallel — scoped to public headers via `-public-headers`.
   4. **Run compliance check** — `abi-compliance-checker -binary -ext -strict`.
   5. **Publish report** — appends the verdict and the report body to the job summary.
   6. **Gate on result** — fails if the ABI is incompatible and SOVERSION was not bumped.

The stages run as a single in-container process because they chain state through
`$GITHUB_ENV`, which does not survive across a `docker run` boundary
(`scripts/abi_check.sh` is the orchestrator that bridges it).

## Consumer requirements

The consumer workflow must, before invoking this action:

- **Configure AWS credentials** with ECR pull access (e.g.
  `aws-actions/configure-aws-credentials`), so the image can be pulled.
- **Checkout with `fetch-depth: 0`** so the base branch history is available for
  the worktree and `git merge-base`.

## Usage

Add a workflow to the library repo (see `aws-c-s3/.github/workflows/check-abi.yml`):

```yaml
jobs:
  check-abi:
    runs-on: ubuntu-24.04
    permissions:
      id-token: write # for configure-aws-credentials OIDC
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

## The SOVERSION escape hatch

An intentional breaking change is allowed: bump `SOVERSION` in the library's
`CMakeLists.txt`. The gate treats an incompatible result (abicc exit 1) as a
pass only when **both** the base and head SONAME versions are readable and they
differ. If the base SONAME cannot be read (or the head build lost its SONAME),
the bump cannot be verified and the gate fails. Tool errors (exit ≥ 2) produce
no trustworthy verdict and can never be cleared by a SOVERSION bump.

## The docker image

The image is defined at `.github/docker-images/ubuntu-22-abi-x64/Dockerfile` and
is built + pushed to ECR (tagged with the builder version) by the
`create-channel.yml` / `create-release.yml` workflows, same as every other
`aws-crt-*` image.

## Layout

```
check-abi/
├── action.yml          # pull image + docker run the orchestrator
├── README.md
└── scripts/
    ├── abi_check.sh    # in-container orchestrator (build->dump->compare->report->gate)
    ├── build.sh        # resolve base ref, worktree, build both refs (parallel)
    ├── dump.sh         # locate both .so, abi-dump both (parallel)
    ├── compare.sh      # abi-compliance-checker; record rc/pct/sovers
    ├── report.py       # write verdict + report body to the job summary
    └── gate.sh         # pass/fail with the SOVERSION escape hatch
```
