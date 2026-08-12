# resolve-pin

Composite action that resolves commit pins from `.github/nightly-pins.yml`. Supports two modes of operation from a single action.

## Mode 1: Single package (C layer)

Look up a pin for one package. Outputs `branch_arg` for the builder's `-b` flag.

```yaml
- name: Resolve pin
  id: resolve-pin
  uses: ./.github/actions/resolve-pin
  with:
    package: ${{ matrix.package }}

- name: Build
  run: ./builder build -p ${{ matrix.package }} ${{ steps.resolve-pin.outputs.branch_arg }}
```

## Mode 2: Submodule update (binding layer)

Update submodule directories to pinned commits or origin/main.

```yaml
- name: Checkout aws-crt-cpp
  uses: actions/checkout@v4
  with:
    repository: awslabs/aws-crt-cpp
    submodules: true

- name: Update submodules from pins
  uses: ./.github/actions/resolve-pin
  with:
    submodule-dirs: "crt/aws-c-* crt/aws-checksums"
```

## Inputs

| Name | Required | Description |
|------|----------|-------------|
| `package` | no | Single package name to resolve. Outputs `branch_arg`. |
| `submodule-dirs` | no | Glob pattern(s) for submodule directories to update in-place. |

At least one of `package` or `submodule-dirs` must be provided.

## Outputs

| Name | Description |
|------|-------------|
| `branch_arg` | `-b <sha>` if pinned, empty otherwise. Only set in `package` mode. |
