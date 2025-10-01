#!/bin/bash
set -e

# checks for previous successful runs on the branch
BRANCH="${GITHUB_REF##*/}"
COMMIT_ID=$(gh run list -w="Dispatcher Workflow" --branch="$BRANCH" --json conclusion,headSha --jq 'first(.[] | select(.conclusion == "success")) | .headSha // empty')
if [[ -z "$COMMIT_ID" ]]; then
    echo "Found no successful dispatch runs on this branch."
    echo "trigger_create=true" >> $GITHUB_OUTPUT
    echo "trigger_sanity_test=true" >> $GITHUB_OUTPUT
    exit 0
fi

# check if new changes on push requires re-running the create-channel
# we look at diffs from the last successful workflow run to current commit
if ! git fetch origin $COMMIT_ID; then
    echo "Failed to fetch commit $COMMIT_ID."
    echo "Setting create and sanity test to true because this might be a new branch with the same name."
    echo "trigger_create=true" >> $GITHUB_OUTPUT
    echo "trigger_sanity_test=true" >> $GITHUB_OUTPUT
    exit 0
fi

SHORT_HASH=$(git rev-parse --short $COMMIT_ID)
COMMIT_MESSAGE=$(git log --format="%s" -n 1 $COMMIT_ID)
echo "Found previous successful run for commit $SHORT_HASH: $COMMIT_MESSAGE"

CHANGED="$(git diff --name-only $COMMIT_ID $GITHUB_SHA)"

echo "---------------------"
echo "CHANGES"
echo "---------------------"
echo "$CHANGED"

CHANGES_THAT_TRIGGER_CREATE="(^\.github/actions/.*)|"\
"(^\.github/workflows/[^/]*\.sh$)|"\
"(^\.github/workflows/(create-channel|dispatcher)\.yml$)|"\
"(^\.github/docker-images/.*$)|"\
"(^builder/.*)"

CHANGES_THAT_TRIGGERED_CREATE=$(echo "$CHANGED" | grep -E "$CHANGES_THAT_TRIGGER_CREATE") || true # job should continue if no matches are found

if [ -n "$CHANGES_THAT_TRIGGERED_CREATE" ]; then
    echo "---------------------"
    echo "CHANGES THAT TRIGGERED CREATE AND SANITY TEST"
    echo "---------------------"
    echo "$CHANGES_THAT_TRIGGERED_CREATE"
    echo "trigger_create=true" >> $GITHUB_OUTPUT
    echo "trigger_sanity_test=true" >> $GITHUB_OUTPUT
else
    echo "No changes detected that would require channel-create flow to run."
    echo "trigger_create=false" >> $GITHUB_OUTPUT

    CHANGES_THAT_DO_NOT_TRIGGER_SANITY_TEST="(^.*\.md$)|(^.gitignore)|(NOTICE)|(LICENSE)"

    if [[ -n $(echo "$CHANGED" | grep -vE "$CHANGES_THAT_DO_NOT_TRIGGER_SANITY_TEST") ]]; then
        echo "---------------------"
        echo "CHANGES THAT TRIGGER SANITY TEST"
        echo "---------------------"
        echo "$CHANGED" | grep -vE "$CHANGES_THAT_DO_NOT_TRIGGER_SANITY_TEST"
        echo "trigger_sanity_test=true" >> $GITHUB_OUTPUT
    else
        echo "No changes detected that would require a sanity test."
        echo "trigger_sanity_test=false" >> $GITHUB_OUTPUT
    fi
fi