#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.
#
# report.py - Append the ABI verdict + the abi-compliance-checker report body
# to $GITHUB_STEP_SUMMARY so the result is visible at a glance on the PR.
#
# Reads state from the environment (set by the earlier steps). Runs with
# `if: always()`, so every field is read defensively.

import os
import re
import sys

import nh3

# abi-compliance-checker's HTML report embeds symbol, type, and enum-member
# names taken directly from the PR's own source -- fully attacker-controlled.
# Piping that into $GITHUB_STEP_SUMMARY unsanitized is an HTML/script
# injection risk (a PR author can name a symbol anything, including
# "<script>...</script>" or an onerror= payload, and it lands verbatim in the
# report). nh3 (the maintained Rust-backed successor to the now-archived
# bleach) strips everything not in this allowlist -- built from inspecting
# abicc 2.3's actual report output, not guessed. In particular: no <script>,
# no <style>, no inline event handlers (onclick etc used for abicc's
# collapsible sections), no <iframe>/<object>/<img>. Losing the
# show/hide-on-click JS behavior is an acceptable tradeoff -- GitHub's own
# markdown renderer strips <script>/onclick from step summaries anyway, so
# that interactivity never worked in this context to begin with.
_ALLOWED_TAGS = {
    'a', 'b', 'br', 'div', 'h1', 'h2', 'hr', 'i', 'span', 'table', 'tbody',
    'td', 'th', 'thead', 'tr',
}
_ALLOWED_ATTRS = {
    'a': {'name', 'class'},
    'div': {'class', 'align', 'id'},
    'span': {'class'},
    'table': {'class'},
    'td': {'class', 'rowspan'},
    'th': {'class', 'rowspan'},
}


def _sanitize_report_html(fragment):
    return nh3.clean(
        fragment,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        link_rel='noopener noreferrer',
    )


def _env(name, default=''):
    return os.environ.get(name, default)


def _verdict_note(rc):
    if rc >= 2:
        return ('**ABI check ERRORED. No verdict was produced — the check could '
                'not run, so no label was applied. See acc.log.**')
    if rc == 1:
        return ('**ABI changed.** This PR is labeled `minor`: the next release '
                'must be at least a minor version bump.')
    if rc == 0:
        return ('**ABI is backward-compatible.** This PR is labeled `patch`.')
    return ''


def _body_fragment(report_html):
    """Return the contents between <body ...> and </body>.

    GitHub step summary expects an HTML fragment, not a full document — sending
    the DOCTYPE and outer <html>/<body> tags makes them render as visible text.
    We strip everything outside <body>...</body> AND the opening <body ...> tag.
    """
    try:
        with open(report_html, encoding='utf-8', errors='replace') as fh:
            html = fh.read()
    except OSError:
        return ''

    # Search after </head> so a stray '<body' token inside the <head>'s
    # <style>/<script> can't be mistaken for the real opening tag.
    head_end = html.find('</head>')
    search_from = head_end if head_end != -1 else 0

    m = re.search(r'<body\b[^>]*>', html[search_from:])
    end = html.rfind('</body>')
    if not m or end == -1:
        return ''

    content_start = search_from + m.end()
    if end < content_start:
        return ''
    return html[content_start:end]


def main():
    summary_path = _env('GITHUB_STEP_SUMMARY')
    if not summary_path:
        print('GITHUB_STEP_SUMMARY not set; skipping summary publish')
        return 0

    lib_name = _env('ABI_LIB_NAME', '(unknown)')
    pct = _env('ABI_PCT', '?')
    src_pct = _env('ABI_SRC_PCT', '?')
    rc_raw = _env('ABI_RC')
    report_html = _env('ABI_REPORT_HTML')
    src_report_html = _env('ABI_SRC_REPORT_HTML')

    try:
        rc = int(rc_raw)
    except (TypeError, ValueError):
        rc = -1

    label = 'patch' if rc == 0 else ('minor' if rc == 1 else 'none')

    lines = [
        '## Check ABI compliance: `{}`'.format(lib_name),
        '',
        '- Binary compatibility: **{}%**'.format(pct),
        '- Source compatibility: **{}%**'.format(src_pct),
        '- Semver label: **{}**'.format(label),
        '- abi-compliance-checker exit code: `{}`'.format(rc if rc >= 0 else 'n/a (failed early)'),
    ]
    note = _verdict_note(rc)
    if note:
        lines += ['', note]

    with open(summary_path, 'a', encoding='utf-8') as out:
        out.write('\n'.join(lines) + '\n')
        fragment = _body_fragment(report_html) if report_html else ''
        if fragment:
            out.write('\n<details><summary>Binary compatibility report</summary>\n\n')
            out.write(_sanitize_report_html(fragment))
            out.write('\n</details>\n')
        src_fragment = _body_fragment(src_report_html) if src_report_html else ''
        if src_fragment:
            out.write('\n<details><summary>Source compatibility report</summary>\n\n')
            out.write(_sanitize_report_html(src_fragment))
            out.write('\n</details>\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
