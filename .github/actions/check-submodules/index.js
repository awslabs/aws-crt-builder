const core = require('@actions/core');
const exec = require('@actions/exec');

// Run an external command.
// cwd: optional string
// check: whether to raise an exception if returnCode is non-zero. Defaults to true.
const run = async function (args, opts = {}) {
    var result = {};
    result.stdout = '';

    var execOpts = {};
    execOpts.listeners = {
        stdout: (data) => {
            result.stdout += data.toString();
        },
    };
    execOpts.ignoreReturnCode = opts.check == false;

    if ('cwd' in opts) {
        execOpts.cwd = opts.cwd;
    }

    result.returnCode = await exec.exec(args[0], args.slice(1), execOpts);
    return result;
}

// Returns array of submodules, where each item has properties: name, path, url
const getSubmodules = async function () {
    const gitResult = await run(['git', 'config', '--file', '.gitmodules', '--list']);
    // output looks like:
    // submodule.aws-common-runtime/aws-c-common.path=crt/aws-c-common
    // submodule.aws-common-runtime/aws-c-common.url=https://github.com/awslabs/aws-c-common.git
    // ...
    const re = /submodule\.(.+)\.(path|url)=(.+)/;

    // build map with properties of each submodule
    var map = {};

    const lines = gitResult.stdout.split('\n');
    for (var i = 0; i < lines.length; i++) {
        const match = re.exec(lines[i]);
        if (!match) {
            continue;
        }

        const submoduleId = match[1];
        const property = match[2];
        const value = match[3];

        let mapEntry = map[submoduleId] || {};
        if (property === 'path') {
            mapEntry.path = value;
            // get "name" from final directory in path
            mapEntry.name = value.split('/').pop()
        } else if (property === 'url') {
            mapEntry.url = value;
        } else {
            continue;
        }

        map[submoduleId] = mapEntry;
    }

    // return array, sorted by name
    return Object.values(map).sort((a, b) => a.name.localeCompare(b.name));
}

// Diff the submodule against its state on origin/main.
// Returns null if they're the same.
// Otherwise returns something like {thisCommit: 'c74534c', mainCommit: 'b6656aa'}
const diffSubmodule = async function (submodule) {
    const gitResult = await run(['git', 'diff', `origin/main`, '--', submodule.path]);
    const stdout = gitResult.stdout;

    // output looks like this:
    //
    // diff --git a/crt/aws-c-auth b/crt/aws-c-auth
    // index b6656aa..c74534c 160000
    // --- a/crt/aws-c-auth
    // +++ b/crt/aws-c-auth
    // @@ -1 +1 @@
    // -Subproject commit b6656aad42edd5d11eea50936cb60359a6338e0b
    // +Subproject commit c74534c13264868bbbd14b419c291580d3dd9141
    try {
        // let's just be naive and only look at the last 2 lines
        // if this fails in any way, report no difference
        var result = {}
        result.mainCommit = stdout.match('\\-Subproject commit ([a-f0-9]{40})')[1];
        result.thisCommit = stdout.match('\\+Subproject commit ([a-f0-9]{40})')[1];
        return result;
    } catch (error) {
        return null;
    }
}

// Returns whether one commit is an ancestor of another.
const isAncestor = async function (ancestor, descendant, cwd) {
    const gitResult = await run(['git', 'merge-base', '--is-ancestor', ancestor, descendant], { check: false, cwd: cwd });
    if (gitResult.returnCode == 0) {
        return true;
    }
    if (gitResult.returnCode == 1) {
        return false;
    }
    throw new Error(`The process 'git' failed with exit code ${gitResult.returnCode}`);
}

// Returns the release tag for a commit, or null if there is none
const getReleaseTag = async function (commit, cwd) {
    const gitResult = await run(['git', 'describe', '--tags', '--exact-match', commit], { cwd: cwd, check: false });
    if (gitResult.returnCode != 0) {
        return null;
    }

    // ensure it's a properly formatted release tag
    const match = gitResult.stdout.match(/^(v[0-9]+\.[0-9]+\.[0-9]+)$/m);
    if (!match) {
        return null;
    }

    return match[1];
}


const checkSubmodules = async function () {
    const submodules = await getSubmodules();
    for (var i = 0; i < submodules.length; i++) {
        const submodule = submodules[i];

        // Diff the submodule against its state on origin/main.
        // If there's no difference, then there's no need to analyze further
        const diff = await diffSubmodule(submodule);
        if (diff == null) {
            continue;
        }

        // Ensure submodule is at an acceptable commit:
        // For repos the Common Runtime team controls, it must be at a tagged release.
        // For other repos, where we can't just cut a release ourselves, it needs to at least be on the main branch.
        const thisTag = await getReleaseTag(diff.thisCommit, submodule.path);
        if (!thisTag) {
            const nonCrtRepo = /^(aws-lc|s2n|s2n-tls)$/
            if (nonCrtRepo.test(submodule.name)) {
                const isOnMain = await isAncestor(diff.thisCommit, 'origin/main', submodule.path);
                if (!isOnMain) {
                    const awslc = /^(aws-lc)$/
                    if (awslc.test(submodule.name)) {
                        // for aws-lc we also use fips-2022-11-02 branch for FIPS support.
                        const isOnFIPS = await isAncestor(diff.thisCommit, 'origin/fips-2022-11-02', submodule.path);
                        if (!isOnFIPS) {
                            core.setFailed(`Submodule ${submodule.name} is using a branch`);
                            return;
                        }
                    } else {
                        core.setFailed(`Submodule ${submodule.name} is using a branch`);
                        return;
                    }
                }
            } else {
                core.setFailed(`Submodule ${submodule.name} is not using a tagged release`);
                return;
            }
        }

        // prefer to use tags for further operations since they're easier to grok than commit hashes
        const mainTag = await getReleaseTag(diff.mainCommit, submodule.path);
        const thisCommit = thisTag || diff.thisCommit;
        const mainCommit = mainTag || diff.mainCommit;

        // freak out if our branch's submodule is older than where we're merging
        if (await isAncestor(thisCommit, mainCommit, submodule.path)) {
            core.setFailed(`Submodule ${submodule.name} is newer on origin/main:`
                + ` ${mainCommit} vs ${thisCommit} on this branch`);
            return;
        }

    }
}

const main = async function () {
    try {
        await checkSubmodules();
    } catch (error) {
        core.setFailed(error.message);
    }
}

main()
