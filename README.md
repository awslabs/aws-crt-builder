## AWS CRT Builder

This is a central repository for build scripts and docker images for the [AWS Common Runtime Team](https://github.com/orgs/awslabs/teams/aws-sdk-common-runtime-team)

## Docker Images
Each docker image has the builder.py script baked into it, with an entrypoint that will call it with the specified arguments
Any push to the .github/docker-images directory will cause a rebuild of all of the docker images(see docker-images.yml). The 
image layers are cached, so this should be quick unless you made a fundamental modification. Any push to builder.py, or any 
python script, will be linted with autopep8 and will trigger a downstream build of enough projects to be sure that they won't 
be broken (see lint.yml/ci.yml)

## Builder
Builder is bundled into a zipapp. Within a given project using builder, builder.json in the root of the project will provide configuration data. 
If you wish to add custom actions or programmatically generate data you can add python scripts in the <root>/.builder/actions directory. All 
scripts in this directory will be loaded and scanned for classes.

### Example action
```python
import Builder

class MyAction(Builder.Action):
    def run(self, env):
        print('My Action did the thing')
```

This can be run with ```builder.pyz run my-action``` or ```builder.pyz run myaction``` or ```builder.pyz run MyAction```

### Action chaining
The ```run(self, env)``` method of any action can return an Action or list of Actions to run before considering this action complete.
The ```Builder.Script``` class can encapsulate a list of python functions, actions, or shell commands to run. Most compound actions
return ```Builder.Script([additional, commands, to, run])```

### The Virtual Shell
There is a virtual shell available via ```env.shell```. It abstracts away dry run behavior, and allows for cross-platform implementations
of common shell operations (cd, cwd, pushd, popd, setenv, getenv, pushenv, popenv, where) and the ```exec()``` function for running 
arbitrary commands.

### Projects
Each project is represented at minimum by its name, path on disk, and github repo url. If there is no builder.json file in the project, nor
any python scripts to describe it, then this is enough for the builder to at least build the project, assuming it will build with defaults
for the current host/target. Projects which declare upstream (dependencies) and downstream (consumers) will get the added benefit of extra
CI checks which will attempt to use a branch with the same name as the current PR, and build the downstream project to see if your changes
work.

## License

This project is licensed under the Apache-2.0 License.

