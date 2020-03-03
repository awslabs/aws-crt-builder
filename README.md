# AWS CRT Builder

This is a central repository for the build tool and docker images for the [AWS Common Runtime Team](https://github.com/orgs/awslabs/teams/aws-sdk-common-runtime-team)

## Using Builder
Builder is bundled into a zipapp. Within a given project using builder, builder.json in the root of the project will provide configuration data. 
If you wish to add custom actions or programmatically generate data you can add python scripts in the <root>/.builder/ directory. All 
scripts in this directory will be loaded and scanned for subclasses of Project, Import, and Action.

### Requirements
* Python 3.4+
* docker (if cross compiling with dockcross)
* CMake 3.1+ (if compiling native code)
* curl (linux only)
* tar (linux only)

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
* ```--platform PLATFORM``` - Platform to cross-compile for (via dockcross, requires docker to be installed)
* ```--build-dir DIR``` - Make a new directory to do all the build work in, instead of using the current directory
* ```--dump-config``` - Dumps the resultant config after merging all available options. Useful for debugging your project configuration.

### Example build
```builder.pyz build --project=aws-c-common downstream```

## Projects
Each project is represented at minimum by its name, path on disk, and github repo url. If there is no builder.json file in the project, nor
any python scripts to describe it, then this is enough for the builder to at least build the project, assuming it will build with defaults
for the current host/target. Projects which declare upstream (dependencies) and downstream (consumers) will get the added benefit of extra
CI checks which will attempt to use a branch with the same name as the current PR, and build the downstream project to see if your changes
work.

### Configuration (builder.json)
Each project has a configuration file: builder.json in the root of the project. It may also have a .builder folder which contains python
scripts that will be automatically loaded when the project is found by the builder. Both of these are techncially optional, if the builder
finds something that looks like a git repo full of code in a directory with the same name as the project it is searching for, it will use
that instead. There are a few external dependencies (s2n and libcrypto, for instance) which are configured by scripts embedded in builder
(see imports/). 

#### Minimal config:
```json
{
    "name": "my-project"
}
```

#### Detailed config:
NOTE: Any key can be prefixed with a ```!``` to overwrite the config value, rather than to add to it.

```json
{
    "name": "my-project",
    // Whether or not this project should be built
    "enabled": true,
    // Steps to run before building. default: []
    "pre_build_steps": [
        "some command or action to run"
    ],
    // Steps to build the project. If not specified, CMake will be run on the project's root directory
    // If you want to invoke the default build as one of your steps, simply use "build" as that step
    "build_steps": [
        "some command or action to run",
        "some other command to run"
    ],
    // Steps to run after building. default: []
    "post_build_steps": [
        "some command or action to run"
    ],
    // Steps to run when testing is requested. If not specified, CTest will be run on the project's binaries directory
    // If you want to invoke the default test path as one of your steps, use "test" as that step's command
    "test_steps": [
        "some command or action to run"
    ],
    // These will be built before my-project, and transitive dependencies will be followed.
    "dependencies": [
        {
            "name": "my-lib",
            "revision": "branch-or-commit-sha"
        }
    ],
    // These will be built when a downstream build is requested
    "consumers": [
        {
            "name": "my-downstream-project"
        }
    ],
    // These are special, much like CMake's IMPORTED targets, the builder must know about them or they must be
    // defined by a script. For examples, look in builder/imports. Just like dependencies, transitive imports
    // will be resolved.
    "imports": [
        "s2n"
    ],
    // Configuration differences per host
    "hosts": {
        "ubuntu": {},
        "debian": {},
        "al2": {},
        "al2012": {},
        "alpine": {},
        "raspbian": {},
        "manylinux": {},
        "macos": {},
        "windows": {}
    },
    // Configuration differences per target platform
    "targets" : {
        "linux": {
            "architectures": {
            "x86": {},
            "x64": {},
            "armv6": {},
            "armv7": {},
            "armv8|aarch64|arm64": {},
            "mips": {}
        },
        "macos": {
            "architectures": {
                "x64": {}
            }
        }, 
        "windows" : {
            "architectures": {
                "x86": {},
                "x64": {}
            }
        }
    },
    // Configuration differences per compiler
    "compilers": {
        "clang": {
            "versions": {
                // example, disable on clang 3
                "3": {
                    "enabled": false
                },
            }
        }
    }
}
```

### Cross-compiling
On linux and macos, builder supports cross compiling via [dockcross](https://github.com/dockcross/dockcross). It installs a small docker
container locally that contains the toolchain and creates a shell to run commands in this environment. Builder then wraps build commands
with that shell.

## Actions
Actions are just arbitrary python code that can be run in place of shell commands. Minimally, Actions derive from ```Builder.Action```
and provide a ```run(self, env)``` method.

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

## Developing on builder
### Docker Images
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

## License

This project is licensed under the Apache-2.0 License.
