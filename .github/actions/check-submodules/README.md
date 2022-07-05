# check-submodules
Scan all submodules in a repo and ensure they're using an official release tag (tag must fit pattern "vX.Y.Z"),
and that the release tag hasn't accidentally rolled backwards.

This is intended for use with the CRT bindings (ex: aws-crt-java).

## Notes on node_modules/
Github Actions tutorials tell you to commit `node_modules/`.
But we don't do that, because then Dependabot will scan all the 3rd-party`package.json`
files and start flagging vulnerabilities in "devDependencies" that don't really affect us.

Instead, the `prepare` script is used to compile `index.js` and ALL dependencies to `dist/index.js`.

The downside is that you must remember to run `npm install` after modifying `index.js`
or any dependencies.

## To update NPM dependencies:
```
cd path/to/aws-crt-builder/.github/actions/check-submodules
npm update
npm install
```

## To run locally:
```sh
# ensure you've compiled the latest changes
cd path/to/aws-crt-builder/.github/actions/check-submodules
npm install

# now run on a specific repo
cd path/to/aws-crt-java
node path/to/aws-crt-builder/.github/actions/check-submodules/dist/index.js
```


