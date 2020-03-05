const core = require('@actions/core');
const fs = require('fs');

try {
    const github_ref = process.env.GITHUB_REF;
    const parts = github_ref.split('/');
    const branch = parts[parts.length - 1];
    var release_tag = branch;
    // GITHUB_REF can be refs/pull/<pr#>/merge for PR openings
    if (branch == 'master' || branch == 'merge') {
        const spawnSync = require('child_process').spawnSync;
        const result = spawnSync('git', ['describe', '--abbrev=0'], {
            timeout: 2000
        });
        if (result.status == 0) {
            release_tag = result.stdout.trim();
        }
    }

    core.setOutput('release_tag', release_tag);
    const output_path = core.getInput('output');
    if (output_path) {
        fs.writeFileSync(output_path, release_tag);
    }
} catch (error) {
    core.setFailed(error.message);
}