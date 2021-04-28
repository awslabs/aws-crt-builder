
import builder.core.api  # force API to load and expose the virtual module
from collections import namedtuple
import os
import unittest
import unittest.mock as mock

from builder.core.env import Env
from builder.core.project import Project
from builder.core.spec import BuildSpec

# base config -- copy for tests
here = os.path.dirname(os.path.abspath(__file__))
test_data_dir = os.path.join(here, 'data')
_test_proj_config = {
    'name': 'test-proj',
    'search_dirs': [test_data_dir],
    'path': here,
}



class TestEnv(unittest.TestCase):

    def setUp(self):
        # remove possible inter test behavior
        Project._projects.clear()

    def test_project_variants(self):
        """project variants should produce a config overridden by variant contents"""
        config = _test_proj_config.copy()
        config['variants'] = {
            'test': {
                'name': 'TEST'
            }
        }

        p = Project(**config)
        spec = BuildSpec()
        env = Env({
            'project': p,
            'args': namedtuple('Args', ['project', 'cli_config'])(None, None),
            'branch': 'main',
            'spec': spec,
            'variant': 'test',
        })
        # env.config should be the variant, not the defaults
        variant = env.config
        self.assertEquals(variant['name'], 'TEST')
