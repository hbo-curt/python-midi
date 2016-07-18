#!/usr/bin/env python

from setuptools import setup
import setuptools.command.install

__base__={
    'name': 'midi',
    'version': '0.3.2',
    'description': 'Python MIDI API',
    'author': 'giles hall',
    'author_email': 'ghall@csh.rit.edu',
    'maintainer': 'curt elsasser',
    'package_dir': {
        'midi': 'src'
        },
    'py_modules': ['midi.__init__', 'midi.containers', 'midi.events', 'midi.util', 'midi.fileio', 'midi.constants'],
    'ext_modules': [],
    'ext_package': '',
    'scripts': ['scripts/mididump.py']
}

# this kludge ensures we run the build_ext first before anything else
# otherwise, we will be missing generated files during the copy
class Install_Command_build_ext_first(setuptools.command.install.install):
    def run(self):
        self.run_command("build_ext")
        return setuptools.command.install.install.run(self)


if __name__ == "__main__":
    setup(**__base__)


