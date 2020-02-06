
from setuptools import setup, find_packages
from subprocess import check_output

git_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
version = 'v0.1-{}'.format(git_branch)
if git_branch == 'master':
    git_rev = check_output(['git', 'describe', '--abbrev=0'])
    version = git_rev

setup(
    name="builder",
    version=version,
    packages=find_packages(),
    scripts=['builder.py'],
    author='AWS SDK Common Runtime Team',
    author_email='aws-sdk-common-runtime@amazon.com',
    project_urls={
        "Source": "https://github.com/awslabs/aws-crt-builder"
    }
)
 
