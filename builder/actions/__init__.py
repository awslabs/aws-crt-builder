# load up all subclasses of Action such that Scripts.load() finds them
from builder.actions.script import Script
from builder.actions.install import InstallPackages, InstallCompiler
from builder.actions.git import DownloadDependencies
from builder.actions.mirror import Mirror
from builder.actions.release import ReleaseNotes
from builder.actions.cmake import CMakeBuild, CTestRun
