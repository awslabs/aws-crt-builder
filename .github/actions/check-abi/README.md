# check-abi

Dump and compare the ABI of a CRT C shared library between a pull request's head
and its base ref, and fail the build on an unauthorized binary-incompatible
change. This is intended for use with the CRT C libraries (ex: aws-c-s3, aws-c-io).

## What it does

1. **Install ABI tools** — `abi-dumper`, `abi-compliance-checker`,
   `universal-ctags`, plus build dependencies (`cmake`, `g++`, `libssl-dev`).
2. **Download builder** — fetches `builder.pyz`; building is the only part that
   needs builder, because builder owns the CRT dependency graph.
3. **Build base and head refs** in parallel — both as shared libs with debug info.
4. **Dump ABI for base and head** in parallel — scoped to public headers via `-public-headers`.
5. **Run compliance check** — `abi-compliance-checker -binary -ext -strict`.
6. **Publish report** — appends the verdict and the report body to the job summary.
7. **Cleanup worktree** — removes the base worktree.
8. **Gate on result** — fails if the ABI is incompatible and SOVERSION was not bumped.

The consumer workflow must checkout with `fetch-depth: 0` so the base branch
history is available for the worktree and `git merge-base`.

## Usage

Add a workflow to the library repo (see `aws-c-s3/.github/workflows/check-abi.yml`):

```yaml
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
| `builder-version` | no | `v0.9.93` | Builder version/channel used to build. |
| `builder-source` | no | `releases` | `releases` for tags, `channels` for branch builds. |
| `builder-host` | no | CloudFront URL | Builder artifact host. |

## The SOVERSION escape hatch

An intentional breaking change is allowed: bump `SOVERSION` in the library's
`CMakeLists.txt`. The gate treats an incompatible result (abicc exit 1) as a
pass only when **both** the base and head SONAME versions are readable and they
differ. If the base SONAME cannot be read (or the head build lost its SONAME),
the bump cannot be verified and the gate fails. Tool errors (exit ≥ 2) produce
no trustworthy verdict and can never be cleared by a SOVERSION bump.

## Layout

```
check-abi/
├── action.yml          # orchestrates the steps below
├── README.md
└── scripts/
    ├── build.sh        # resolve base ref, worktree, build both refs (parallel)
    ├── dump.sh         # locate both .so, abi-dump both (parallel)
    ├── compare.sh      # abi-compliance-checker; record rc/pct/sovers
    ├── report.py       # write verdict + report body to the job summary
    └── gate.sh         # pass/fail with the SOVERSION escape hatch
```
