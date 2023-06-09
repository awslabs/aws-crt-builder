# AWS CRT Builder

This is a central repository for the build tool and docker images for the [AWS Common Runtime Team](https://github.com/orgs/awslabs/teams/aws-sdk-common-runtime-team)

## Using Builder
Builder is bundled into a zipapp. Within a given project using builder, builder.json in the root of the project will provide configuration data.
If you wish to add custom actions or programmatically generate data you can add python scripts in the <root>/.builder/ directory. All
scripts in this directory will be loaded and scanned for subclasses of Project, Import, and Action.

### Requirements
* Python 3.5+
* docker (if cross compiling with dockcross)
* CMake 3.1+ (if compiling native code)

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
  * Valid values are anything that you could get from `uname`.lower() - `uname -m`, e.g. linux-x86_64, linux-x64. See targets below.
* ```--build-dir DIR``` - Make a new directory to do all the build work in, instead of using the current directory
* ```--dump-config``` - Dumps the resultant config after merging all available options. Useful for debugging your project configuration.
* ```--cmake-extra``` - Extra cmake config arg applied to all projects. e.g ```--cmake-extra=-DBUILD_SHARED_LIBS=ON```. May be specified multiple times.
* ```--coverage``` - Generate the test coverage report and upload it to codecov. Only supported when using cmake and gcc as compiler, error out on other cases. Use `--coverage-include` and `--coverage-exclude` to report the needed coverage file. The default code coverage report will include everything in the `source/` directory
    * ```--coverage-include``` - The relative (based on the project directory) path of files and folders to include in the test coverage report. May be specified multiple times.
    * ```--coverage-exclude``` - The relative (based on the project directory) path of files and folders to exclude in the test coverage report. May be specified multiple times. Note: the include can override the exclude path.

### Supported Targets:
* linux: x86|i686, x64|x86_64, armv6, armv7, arm64|armv8|aarch64|arm64v8
* macos|darwin: x64|x86_64
* windows: x86, x64
* freebsd: x64
* openbsd: x64

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
scripts that will be automatically loaded when the project is found by the builder. Both of these are technically optional, if the builder
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
      Any key can be prefixed with a ```+``` to force a value to be added to an array.

See builder/data.py for more info/defaults/possible values.

```jsonc
{
    "name": "my-project",
    // Whether or not this project should be built
    "enabled": true,
    // Whether or not this project needs a C/C++ compiler
    "needs_compiler": true,

    // Variables for use in interpolation throughout the config. Note that these can be overridden
    // per host/os/target/architecture/compiler/version (see below)
    // Variables can be references in braces: e.g. {my_variable}
    //
    // The following variables are pre-defined by builder internally:
    // * host - the host OS
    // * compiler - the compiler that will be used if project needs a compiler
    // * version - the compiler version
    // * target - the target OS class (linux/windows/macos/android)
    // * arch - the target arch
    // * cwd - the current working directory (affected by --build-dir argument)
    // * source_dir - The source directory for the project being built
    // * root_dir - The source directory for the root project. In the case of a single build this is the same as {source_dir}. When
    //                building upstream/downstream projects it refers to the original (root) project source directory.
    // * build_dir - The directory where intermediate build artifacts will be generated (defaults to "{source_dir}/build")
    // * deps_dir - The root directory where dependencies will be installed (defaults to "{build_dir}/deps")
    // * install_dir - The output directory for the build, where final artifacts will be installed (defaults to "{build_dir}/install")
    "variables": {
        "my_project_version": "1.0-dev"
    },

    // For each of these packages keys, they may be prefixed with specific package managers:
    // e.g. "apt_packages"
    // Supported package managers are:
    // * apt (Debian/Ubuntu)
    // * yum (Red Hat/CentOS/Amazon Linux)
    // * brew (OSX)
    // * choco (Windows)
    // * apk (Android)
    // * pkg (FreeBSD)
    // Packages to install when a compiler is required (build tools, gcc-multilib, etc)
    "compiler_packages": [],
    // Packages to install to allow building and testing to work (languages, squid, other CI tools, etc)
    "packages": [],

    // If using the default build (which will invoke cmake), additional arguments to be passed to cmake
    "cmake_args": ["-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],

    // Additional directories to search to find imports, dependencies, consumers before searching GitHub for them
    "search_dirs": [],

    // environment variables
    "pre_build_env": {} # environment variable(s) for pre_build_steps
    "build_env": {} # environment variable(s) for build_steps
    "post_build_env": {} # environment variable(s) for build_steps
    "env": {} # environment variable(s) for all build steps. Shorthand for setting same variables in each env

    // Steps to run before building. default: []
    "pre_build_steps": [
        "echo '{my_project_version}' > version.txt" // see variables section
    ],

    // Steps to build the project. If not specified, CMake will be run on the project's root directory
    // If you want to invoke the default build as one of your steps, simply use "build" as that step
    "build_steps": [
        "mvn compile",
        "./gradlew build"
    ],
    // Steps to run after building. default: []
    "post_build_steps": [
        "mvn package",
        "./gradlew publishToMavenLocal"
    ],
    // Steps to run when testing is requested. If not specified, CTest will be run on the project's binaries directory
    // If you want to invoke the default test path as one of your steps, use "test" as that step's command
    "test_steps": [
        "mvn test",
        "./gradlew test"
    ],

    // These will be built before my-project, and transitive dependencies will be followed. Alias: upstream
    "dependencies": [
        {
            "name": "my-lib",
            "revision": "branch-or-commit-sha"
        }
    ],
    // These will be built when a downstream build is requested. Alias: downstream
    "consumers": [
        {
            "name": "my-downstream-project"
        }
    ],
    // These are special, much like CMake's IMPORTED targets, the builder must know about them or they must be
    // defined by a script. For examples, look in builder/imports. Just like dependencies, transitive imports
    // will be resolved. If no special configuration is required, these can just be submodules or other repos
    "imports": [
        "s2n"
    ],

    // Per-environment overrides
    // Overrides are applied per host, per target/architecture, and per compiler/version. Any top-level config
    // value can be overridden from within these override sections, see below for examples.

    // Configuration differences per host (the machine/image the build runs on)
    // Any host not specified will be built with default values from the rest of the config
    "hosts": {
        "linux": {}, // includes all flavors of linux below
        "ubuntu": {},
        "debian": {},
        "al2": {},
        "al2012": {
            "enabled": false // example: disable building on AL2012
        },
        "alpine": {},
        "raspbian": {},
        "manylinux": {},
        "musllinux": {},
        "macos": {},
        "windows": {}
    },

    // Configuration differences per target platform (the machine being built for)
    // Any target not specified will be built with default values from the rest of the config
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
                "x86": {
                    "enabled": false // example: don't build for Windows 32 bit
                },
                "x64": {}
            }
        },
        "android" : {

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
    },
    // Build variants, accessible via --variant=<myvariant>
    // Variants can override any setting, they will be overlaid on the default config
    "variants" : {
        "no-tests": {
            "!test_steps": []
        },
        "tsan": {
            "compilers": {
                "clang": {
                    "cmake_args": [
                        "-DENABLE_SANITIZERS=ON",
                        "-DSANTIZERS=,thread"
                    ]
                }
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

See api.py for the available API to actions. See https://github.com/awslabs/aws-crt-python/tree/main/.builder/actions for examples.

#### Action chaining
The ```run(self, env)``` method of any action can return an Action or list of Actions to run before considering this action complete.
The ```Builder.Script``` class can encapsulate a list of python functions, actions, or shell commands to run. Most compound actions
return ```Builder.Script([additional, commands, to, run])```

#### The Virtual Shell
There is a virtual shell available via ```env.shell```. It abstracts away dry run behavior, and allows for cross-platform implementations
of common shell operations (cd, cwd, pushd, popd, setenv, getenv, pushenv, popenv, where) and the ```exec()``` function for running
arbitrary commands.

## Developing on builder

Install the package locally to your virtual environment in development mode:

```
pip install -e .
```

The `builder.main` console script will be added to your path automatically and changes are reflected "live".

### Debugging
When debugging builder locally, use whatever python debugger you wish. You can also feed it the following command line arguments to ease the
debugging experience:
* --skip-install - don't install packages, assume they're already there
* --build-dir=/path/to/other/git/repo - will jump to this directory before starting execution, helpful for debugging another project's
                                        configuration and build scripts

When debugging builder from downstream CI (AWS common runtime repos), to use a branch of builder, you will need to change `BUILDER_VERSION` to the branch name of aws-crt-builder, and the `BUILDER_SOURCE` to be `channels` from `ci.yml`. Eg: for `aws-crt-java`, make those change to the [here](https://github.com/awslabs/aws-crt-java/blob/main/.github/workflows/ci.yml#L10-L11).

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
libcrypto, cmake (manylinux2014-x86), and maven (ARM) are built in their target containers by the build_cmake.sh,
build_libcrypto*.sh and cache_maven.sh scripts. These can be run in GitHub, or on a local machine. They upload the build results
of each of those packages to S3, for distribution via CloudFront to images as they are being built. Since these don't change much,
this shouldn't be a common operation, but it is automated.

## License

This project is licensed under the Apache-2.0 License.
