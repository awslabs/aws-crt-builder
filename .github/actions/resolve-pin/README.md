# resolve-pin

Composite action that checks if a package is pinned to a specific commit in `.github/nightly-pins.yml`.

## Usage

```yaml
- name: Resolve pin
  id: resolve-pin
  uses: ./.github/actions/resolve-pin
  with:
    package: ${{ matrix.package }}

- name: Build
  run: ./builder build -p ${{ matrix.package }} ${{ steps.resolve-pin.outputs.branch_arg }}
```

## Inputs

| Name | Required | Description |
|------|----------|-------------|
| `package` | yes | Package name to look up in the pins file |

## Outputs

| Name | Description |
|------|-------------|
| `branch_arg` | `-b <sha>` if pinned, empty string otherwise |

## How it works

1. Sparse-checks out `.github/nightly-pins.yml` from the current repo
2. Greps for the package name under the `pins:` section
3. If found, outputs `-b <commit-sha>` which the builder uses to check out that commit instead of main
