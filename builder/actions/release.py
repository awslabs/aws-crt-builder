# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import argparse
import os
import re
import sys

from action import Action
from actions.script import Script


def print_release_notes(env):
    sh = env.shell

    def warn(msg):
        if args.ignore_warnings:
            print("[WARNING]", msg)
        else:
            print(msg + "\nrun with --ignore-warnings to proceed anyway")
            sys.exit(1)

    def get_all_tags():
        git_output = sh.exec('git', 'show-ref', '--tags', quiet=True).output
        tags = []
        for line in git_output.splitlines():
            # line looks like: "e18f041a0c8d17189f2eae2a32f16e0a7a3f0f1c refs/tags/v0.5.18"
            match = re.match(
                r'([a-f0-9]+) refs/tags/(v([0-9]+)\.([0-9]+)\.([0-9]+))', line)
            if not match:
                # skip malformed release tags
                continue
            tags.append({
                'commit': match.group(1),
                'str': match.group(2),
                'num_tuple': (int(match.group(3)), int(match.group(4)), int(match.group(5))),
            })
        # sort highest version first
        return sorted(tags, reverse=True, key=lambda tag: tag['num_tuple'])

    def get_tag_for_commit(tags, commit):
        for tag in tags:
            if tag['commit'] == commit:
                return tag

    def get_current_commit():
        git_output = sh.exec('git', 'rev-parse', 'HEAD', quiet=True).output
        return git_output.splitlines()[0]

    parser = argparse.ArgumentParser(
        description="Help gather release notes for CRTs")
    parser.add_argument('--ignore-warnings',
                        action='store_true', help="ignore warnings")
    args = parser.parse_known_args(env.args.args)[0]

    crt_path = sh.cwd()
    submodules_root_path = os.path.join(crt_path, 'aws-common-runtime')
    if not os.path.exists(submodules_root_path):
        print('Must be run from an "aws-crt-*" dir')
        sys.exit(1)

    print('Syncing to latest master...')
    sh.exec('git', 'checkout', 'master', quiet=True)
    sh.exec('git', 'pull', quiet=True)
    sh.exec('git', 'submodule', 'update', '--init', quiet=True)

    print('Gathering info...')
    crt_tags = get_all_tags()
    crt_latest_tag = crt_tags[0]

    crt_changes = sh.exec(
        'git', 'log', crt_latest_tag['commit'] + '..', quiet=True).output
    if not crt_changes:
        print('No changes since last release', crt_latest_tag['str'])
        sys.exit(1)

    submodules = []
    submodule_names = sorted(os.listdir(submodules_root_path))
    for submodule_name in submodule_names:
        submodule = {'name': submodule_name,
                     'path': os.path.join(submodules_root_path, submodule_name)}
        if submodule_name == 's2n' or not os.path.isdir(submodule['path']):
            continue
        submodules.append(submodule)
        sh.cd(submodule['path'], quiet=True)
        sh.exec('git', 'fetch', quiet=True)
        submodule['tags'] = get_all_tags()
        submodule['current_commit'] = get_current_commit()
        submodule['current_tag'] = get_tag_for_commit(
            submodule['tags'], submodule['current_commit'])
        newest_tag = submodule['tags'][0]
        if submodule['current_tag'] != newest_tag:
            warn('{} not at newest release: {} < {}'.format(
                submodule['current_tag']['str'], newest_tag['str']))

    print('Syncing to previous CRT release {}...'.format(
        crt_latest_tag['str']))
    sh.cd(crt_path, quiet=True)
    sh.exec('git', 'checkout', crt_latest_tag['str'], quiet=True)
    sh.exec('git', 'submodule', 'update', '--init', quiet=True)

    print('Gathering info...')
    for submodule in submodules:
        sh.cd(submodule['path'], quiet=True)
        submodule['prev_commit'] = get_current_commit()
        submodule['prev_tag'] = get_tag_for_commit(
            submodule['tags'], submodule['prev_commit'])

    print('Syncing back to latest...')
    sh.exec('git', 'checkout', 'master', quiet=True)
    sh.exec('git', 'submodule', 'update', '--init', quiet=True)

    print('------ Submodule changes ------')
    for submodule in submodules:
        # Special warning about API breakages
        major_change = False
        if submodule['current_tag']['num_tuple'][0] == 0:
            if submodule['prev_tag']['num_tuple'][1] != submodule['current_tag']['num_tuple'][1]:
                major_change = True
        elif submodule['prev_tag']['num_tuple'][0] != submodule['current_tag']['num_tuple'][0]:
            major_change = True
        if major_change:
            print('MAJOR CHANGE: {} {} -> {}'.format(
                submodule['name'],
                submodule['prev_tag']['str'],
                submodule['current_tag']['str']))

        # Link to release notes
        # We can just dump text because these are a github thing, not a git thing
        for tag in submodule['tags']:
            if tag == submodule['prev_tag']:
                break
            print(
                'https://github.com/awslabs/{}/releases/tag/{}'.format(submodule['name'], tag['str']))

    print('------ CRT changes ------')
    print(crt_changes)


class ReleaseNotes(Action):
    def is_main(self):
        return True

    def run(self, env):
        print_release_notes(env)
