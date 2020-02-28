# AWS CRT Builder

This is a central repository for build scripts and docker images for the [AWS Common Runtime Team](https://github.com/orgs/awslabs/teams/aws-sdk-common-runtime-team)

## Builder
Builder is bundled into a zipapp. Within a given project using builder, builder.json in the root of the project will provide configuration data. 
If you wish to add custom actions or programmatically generate data you can add python scripts in the <root>/.builder/actions directory. All 
scripts in this directory will be loaded and scanned for classes.

### CLI Arguments
Usage: ```builder.pyz [build|inspect|<action-name>] [spec] [OPTIONS]```
* ```build``` - Build the project using either the steps in the builder.json project, or via the default CMake build/test actions
* ```inspect``` - Inspect the current host, and report what compilers and tools the builder can find
* ```<action-name>``` - Runs the named action, either from within builder or your project
* ```[spec]``` - Specs are of the form host-compiler-version-target-arch\[-downstream\]. Any part can be replaced with ```default```, 
                 and ```default-downstream``` and ```downstream``` are also valid (and equivalent to each other)
* ```-p|--project PROJECT``` - Specifies the project to look for locally. If the project is not found, it will be cloned from GitHub
* ```--spec SPEC``` - Force a spec to be used. See \[spec\] above
* ```--branch BRANCH``` - Branch to use for the target project
* ```--config CONFIG``` - CMake config to use (Debug, Release, RelWithDebInfo, DebugOpt) Default is RelWithDebInfo
* ```--compiler COMPILER[-VERSION]``` - Use the specified compiler, installing it if necessary
* ```--build-dir DIR``` - Make a new directory to do all the build work in, instead of using the current directory
* ```--dump-config``` - Dumps the resultant config after merging all available options. Useful for debugging your project configuration.

### Example build
```builder.pyz build --project=aws-c-common downstream```

### Example action
```python
import Builder

class MyAction(Builder.Action):
    def run(self, env):
        print('My Action did the thing')
```

This can be run with ```builder.pyz my-action``` or ```builder.pyz myaction``` or ```builder.pyz MyAction```

See api.py for the available API to actions.

#### Action chaining
The ```run(self, env)``` method of any action can return an Action or list of Actions to run before considering this action complete.
The ```Builder.Script``` class can encapsulate a list of python functions, actions, or shell commands to run. Most compound actions
return ```Builder.Script([additional, commands, to, run])```

#### The Virtual Shell
There is a virtual shell available via ```env.shell```. It abstracts away dry run behavior, and allows for cross-platform implementations
of common shell operations (cd, cwd, pushd, popd, setenv, getenv, pushenv, popenv, where) and the ```exec()``` function for running 
arbitrary commands.

## Projects
Each project is represented at minimum by its name, path on disk, and github repo url. If there is no builder.json file in the project, nor
any python scripts to describe it, then this is enough for the builder to at least build the project, assuming it will build with defaults
for the current host/target. Projects which declare upstream (dependencies) and downstream (consumers) will get the added benefit of extra
CI checks which will attempt to use a branch with the same name as the current PR, and build the downstream project to see if your changes
work.

### Configuration (builder.json)

## Docker Images
Each docker image has a script which will fetch the builder app baked into it, and will then call the builder with the arguments provided.
Any push to the .github/docker-images directory will cause a rebuild of all of the docker images (see docker-images.yml). The 
image layers are cached, so this should be quick unless you made a fundamental modification. Any push to the builder source, or any 
python script, will be linted with autopep8 and will trigger a downstream build of enough projects to be sure that they won't 
be broken (see lint.yml/sanity-test.yml)

Installed on these docker images:
* maven, plus cached dependencies for building aws-crt-java
* CMake 3, CTest
* git
* python3 + pip, setuptools, virtualenv, autopep8
* awscli
* Linux only: libcrypto, libcrypto.a compiled with -fPIC (/opt/openssl)
* Linux only: curl, bash

### Installed Binary packages
libcrypto, cmake (manylinux1, manylinux2014-x86), and maven (ARM) are built in their target containers by the build_cmake.sh,
build_libcrypto*.sh and cache_maven.sh scripts. These can be run in GitHub, or on a local machine. They upload the build results
of each of those packages to S3, for distribution via CloudFront to images as they are being built. Since these don't change much,
this shouldn't be a common operation, but it is automated.

### Non-intel Images
ARM images are built via ```docker buildx``` and are running using ARM binaries.

## License

This project is licensed under the Apache-2.0 License.
