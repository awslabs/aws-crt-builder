"""The CI gate: assert a pull request's title and its fragment agree."""

from fragments import CATEGORY, VALID_TYPES, _err, parse_title, \
    validate_fragment
from pathlib import Path
import json
import sys


def check_fragment_changes(args, pr_type, reason):
    """Assert the PR's changes under `prefix` are exactly one new fragment.

    Returns an exit code to stop on, or None to carry on with the usual checks --
    including when the pull request touches nothing under the changes directory,
    which is the ordinary "author forgot" case the fragment check reports below.
    """
    prefix = args.changes_prefix.rstrip("/")
    expected = f"{prefix}/preview/{args.pr}.json"
    rows = (ln.strip().partition("\t")
            for ln in Path(args.changed_paths_file).read_text().splitlines())
    entries = [(status, p) for status, _, p in rows if p.startswith(f"{prefix}/")]

    if not entries:
        return None

    wrong = [(st, p) for st, p in entries if p != expected]
    if wrong:
        listed = "\n".join(f"         {st:<10} {p}" for st, p in wrong)
        _err(
            f"a `{pr_type}` change may only add its own changelog fragment.\n"
            f"       expected exactly one new file:\n"
            f"         added      {expected}\n"
            f"       but this pull request also changes:\n{listed}\n"
            f"       A fragment named for another pull request renders under that\n"
            f"       number; one at another path renders nowhere, and a released\n"
            f"       entry is already published.")
        reason("stray-fragment")
        return 1

    status = entries[0][0]
    if status != "added":
        _err(
            f"{expected} is `{status}` in this pull request, not `added`.\n"
            f"       That path already exists on the base branch, so this pull\n"
            f"       request is rewriting a released or in-flight entry rather than\n"
            f"       contributing its own. Move the change to a new fragment.")
        reason("modified-fragment")
        return 1

    return None


def cmd_check(args):
    """CI gate. Exit 0 pass, 1 author-fixable, 2 caller error.

    Two independent assertions:
      * the PR title follows the convention, so a type can be derived at all;
      * a fragment exists and agrees with that type -- unless the type is
        exempt (chore), or the author is a bot we waive.

    One machine-readable reason goes to stdout so a caller can tell an author who
    does not know the convention -- missing-fragment, which earns a template -- from
    one who does, where the diagnostic is the whole response.
    """
    title = (args.title or "").strip()
    frag = Path(args.changes_dir) / "preview" / f"{args.pr}.json"

    def reason(tag):
        print(f"CHANGELOG_CHECK_REASON::{tag}")

    if args.bot_author:
        print(f"OK: #{args.pr} is authored by a bot ({args.bot_author}); "
              "title convention and changelog fragment both waived")
        reason("waived-bot")
        return 0

    if not title:
        _err("--title is required to derive the change type")
        return 2

    pr_type, _summary = parse_title(title)
    if pr_type is None:
        _err(
            f'PR title does not follow the convention: "{title}"\n'
            f"       expected `<type>: <summary>` with type one of "
            f"{sorted(VALID_TYPES)}, an optional scope such as `chore(ci):`,\n"
            f'       or the Revert button\'s `Revert "<original title>"`.')
        reason("bad-title")
        return 1

    if pr_type not in CATEGORY:
        print(f"OK: #{args.pr} is a `{pr_type}` change; no changelog fragment required")
        reason("exempt-type")
        return 0

    if args.changed_paths_file:
        rc = check_fragment_changes(args, pr_type, reason)
        if rc is not None:
            return rc

    if not frag.exists():
        _err(
            f"no changelog fragment for PR #{args.pr}.\n"
            f"       expected: {frag}\n"
            f"       a `{pr_type}` change is customer-visible, so it needs an entry.\n"
            f"       commit that file with this pull request -- a ready-to-paste\n"
            f"       template is in this run's summary, and is commented here too\n"
            f"       when CI has a token that can write.")
        reason("missing-fragment")
        return 1

    errs = validate_fragment(frag)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        reason("invalid-fragment")
        return 1

    data = json.loads(frag.read_text())
    declared_pr = data.get("pr")
    if declared_pr != args.pr:
        _err(
            f"{frag} declares pr={declared_pr} but this PR is #{args.pr}")
        reason("pr-mismatch")
        return 1

    if data.get("type") != pr_type:
        _err(
            f'type mismatch. The PR title says `{pr_type}` but {frag} says '
            f'`{data.get("type")}`.\n'
            f"       Fix whichever is wrong -- they must agree.")
        reason("type-mismatch")
        return 1

    print(f"OK: #{args.pr} title is `{pr_type}` and its fragment is present and valid")
    reason("ok")
    return 0
