#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.
#
# report.py - Append the ABI verdict + the abidiff output to
# $GITHUB_STEP_SUMMARY so the result is visible at a glance on the PR.
#
# Reads state from the environment (set by the earlier steps). Runs with
# `if: always()`, so every field is read defensively.
#
# Unlike abi-compliance-checker, abidiff has no HTML report mode -- its output
# is plain text, so it is embedded as a fenced code block instead of an HTML
# fragment.

import os
import sys


def _env(name, default=''):
    return os.environ.get(name, default)


def _verdict_note(rc):
    if rc < 0:
        return ''
    if rc & 3:
        return ('**ABI check ERRORED. No verdict was produced — the check could '
                'not run, so no label was applied. See abidiff.log.**')
    if rc & 8:
        return ('**ABI changed incompatibly.** This PR is labeled `minor`: the '
                'next release must be at least a minor version bump.')
    return '**ABI is backward-compatible.** This PR is labeled `patch`.'


def main():
    summary_path = _env('GITHUB_STEP_SUMMARY')
    if not summary_path:
        print('GITHUB_STEP_SUMMARY not set; skipping summary publish')
        return 0

    lib_name = _env('ABI_LIB_NAME', '(unknown)')
    rc_raw = _env('ABI_RC')
    diff_log = _env('ABI_DIFF_LOG')

    try:
        rc = int(rc_raw)
    except (TypeError, ValueError):
        rc = -1

    label = 'none'
    if rc >= 0 and not (rc & 3):
        label = 'minor' if (rc & 8) else 'patch'

    lines = [
        '## Check ABI compliance: `{}`'.format(lib_name),
        '',
        '- Semver label: **{}**'.format(label),
        '- abidiff exit code: `{}`'.format(rc if rc >= 0 else 'n/a (failed early)'),
    ]
    note = _verdict_note(rc)
    if note:
        lines += ['', note]

    diff_text = ''
    if diff_log:
        try:
            with open(diff_log, encoding='utf-8', errors='replace') as fh:
                diff_text = fh.read()
        except OSError:
            diff_text = ''

    with open(summary_path, 'a', encoding='utf-8') as out:
        out.write('\n'.join(lines) + '\n')
        if diff_text:
            out.write('\n<details><summary>abidiff output</summary>\n\n')
            out.write('```\n{}\n```\n'.format(diff_text.strip()))
            out.write('\n</details>\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
