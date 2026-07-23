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
    'a': {'name', 'class', 'href'},
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
        # abicc's own report hrefs are same-page anchors (#Top, #Headers) or
        # a single fixed link to its own GitHub page -- never derived from
        # PR-controlled symbol/type names, so allowing href doesn't reopen
        # the injection risk this sanitizer exists for. Restricting to
        # http/https (fragment-only hrefs like "#Top" aren't scheme-prefixed
        # and pass through regardless) still blocks a javascript: URL from
        # ever landing here, in case abicc's report format ever changes.
        url_schemes={'http', 'https'},
    )


def _env(name, default=''):
    return os.environ.get(name, default)


def _verdict_field(report_html, field):
    """Read one integer field out of a report's structured verdict comment.

    e.g. <!-- verdict:incompatible;removed:1;type_problems_high:0;...  -->
    Mirrors gate.sh's verdict_field() -- keep the two in sync; this is the
    same three-way decision restated in Python since report.py can't easily
    shell out to gate.sh's bash function (report.py runs after but its
    ABI_LABEL_RESULT parsing already happened in gate.sh; this copy is just
    for rendering the human-facing "why" note, not for choosing the label).
    """
    if not report_html:
        return 0
    try:
        with open(report_html, encoding='utf-8', errors='replace') as fh:
            first_line = fh.readline()
    except OSError:
        return 0
    m = re.search(r'{}:(\d+)'.format(re.escape(field)), first_line)
    return int(m.group(1)) if m else 0


def _axis_has_real_problem(report_html):
    return any(
        _verdict_field(report_html, f) > 0
        for f in (
            'removed', 'type_problems_high', 'type_problems_medium',
            'interface_problems_high', 'interface_problems_medium',
            'changed_constants',
        )
    )


def _compute_label(rc, report_html, src_report_html, removed_constants_count):
    """Three-way label, mirroring gate.sh exactly -- see gate.sh for the full
    rationale (abicc's own verdict/exit code conflates harmless Low-severity
    renames with real breaks, and a source break is always unconditionally
    reportable regardless of what the binary axis shows)."""
    if rc >= 2:
        return None
    src_broken = _axis_has_real_problem(src_report_html) or removed_constants_count > 0
    bin_broken = _axis_has_real_problem(report_html)
    if src_broken:
        return 'needs-review'
    if bin_broken:
        return 'minor'
    return 'patch'


def _verdict_note(label, removed_constants_count):
    if label is None:
        return ('**ABI check ERRORED. No verdict was produced — the check could '
                'not run, so no label was applied. See acc.log.**')
    if label == 'needs-review':
        note = ('**Source (API) compatibility is broken.** Callers fail to '
                'recompile against the new headers. This PR is labeled '
                '`needs-review` -- a maintainer must confirm this is either an '
                'intentional, acceptable break (and can be relabeled `minor`) '
                'or should be reverted.')
        if removed_constants_count > 0:
            note += (' Includes {} removed macro/enum constant(s) that '
                     'abi-compliance-checker does not detect on its own.'
                     .format(removed_constants_count))
        return note
    if label == 'minor':
        return ('**Binary compatibility changed, but source (API) compatibility '
                'is intact.** This PR is labeled `minor`.')
    return '**ABI and API are backward-compatible.** This PR is labeled `patch`.'


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
    removed_constants_count = int(_env('ABI_REMOVED_CONSTANTS_COUNT', '0') or '0')
    removed_constants_file = _env('ABI_REMOVED_CONSTANTS_FILE')

    try:
        rc = int(rc_raw)
    except (TypeError, ValueError):
        rc = -1

    label = _compute_label(rc, report_html, src_report_html, removed_constants_count)
    label_display = label if label is not None else 'none'

    lines = [
        '## Check ABI compliance: `{}`'.format(lib_name),
        '',
        '- Binary compatibility: **{}%**'.format(pct),
        '- Source compatibility: **{}%**'.format(src_pct),
        '- Semver label: **{}**'.format(label_display),
        '- abi-compliance-checker exit code: `{}`'.format(rc if rc >= 0 else 'n/a (failed early)'),
    ]
    note = _verdict_note(label, removed_constants_count)
    if note:
        lines += ['', note]

    if removed_constants_count > 0 and removed_constants_file:
        try:
            with open(removed_constants_file, encoding='utf-8', errors='replace') as fh:
                names = [n.strip() for n in fh if n.strip()]
        except OSError:
            names = []
        if names:
            lines += ['', '**Removed macro/enum constants:**']
            lines += ['- `{}`'.format(n) for n in names]

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
