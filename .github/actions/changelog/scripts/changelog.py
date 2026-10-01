#!/usr/bin/env python3
"""Changelog fragment tooling: seed, check, render, rollup.

A fragment per pull request under `.changes/preview/`. A release renders those
into CHANGELOG.md and deletes them, so the rendered file is the record and
`.changes/` only ever holds what has not shipped yet.

  .changes/preview/<pr>.json   awaiting release; written by the pull request author
  CHANGELOG.md                 the record: one section per release, newest first
"""
import argparse
import sys

from check import cmd_check
from fragments import cmd_seed
from release import cmd_rollup
from render import cmd_render



def main(argv=None):
    p = argparse.ArgumentParser(prog="changelog")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seed",
                       help="write the template a missing fragment should be filled from")
    s.add_argument("--pr", type=int, required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--out", required=True,
                   help="Where to write it; never inside the changes directory.")
    s.set_defaults(func=cmd_seed)

    c = sub.add_parser("check", help="CI: assert the PR title and its fragment are valid")
    c.add_argument("--pr", type=int, required=True)
    c.add_argument("--title", default="", help="PR title; the change type is derived from it")
    c.add_argument("--bot-author", default="",
                   help="login of the PR author when it is a bot; waives both checks")
    c.add_argument("--changes-dir", default=".changes")
    c.add_argument("--changed-paths-file", default="",
                   help="file of `status<TAB>path` lines for the PR's changes under .changes/")
    c.add_argument("--changes-prefix", default=".changes",
                   help="repo-relative changes directory, for matching changed paths")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("render", help="refresh the unreleased region from preview/")
    r.add_argument("--changes-dir", default=".changes")
    r.add_argument("--changelog", default="CHANGELOG.md")
    r.set_defaults(func=cmd_render)

    u = sub.add_parser("rollup", help="cut a release: render preview/ and drop it")
    u.add_argument("--version", required=True)
    u.add_argument("--date", required=True)
    u.add_argument("--changes-dir", default=".changes")
    u.add_argument("--changelog", default="CHANGELOG.md")
    u.add_argument("--docs-branch", default="docs",
                   help="Branch named in the pointer to the unreleased changes.")
    u.add_argument("--minor-prs", default="",
                   help="Comma-separated PRs carrying the `minor` label; "
                        "their entries render under Possible Breaking Changes.")
    u.set_defaults(func=cmd_rollup)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
