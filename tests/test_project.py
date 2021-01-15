import unittest
import unittest.mock as mock

from builder.core.project import Project
from builder.actions.script import Script
from builder.core.action import Action

import os
here = os.path.dirname(os.path.abspath(__file__))

test_data_dir = os.path.join(here, 'data')

# base config -- copy for tests
_test_proj_config = {
    'name': 'test-proj',
    'search_dirs': [test_data_dir],
    'path': here,
}


def _collect_steps(out, step):
    """
    collect the list of steps
    """
    if isinstance(step, list):
        for s in step:
            _collect_steps(out, s)
    elif isinstance(step, Script):
        out.append(str(step))
        _collect_steps(out, step.commands)
    else:
        out.append(str(step))


def _fuzzy_find_step(step, name):
    """
    attempt to find a step name or value that either matches name or contains name as a fragment
    """
    step_stack = []
    _collect_steps(step_stack, step)
    for s in step_stack:
        if s == name or name in s:
            return s
    return None


def _step_exists(step, name):
    """
    test if the step [name] exists in the set of [step]s
    """
    return _fuzzy_find_step(step, name) is not None


def _dump_step(step):
    import pprint
    steps = []
    _collect_steps(steps, step)
    pprint.pprint(steps)


class TestProject(unittest.TestCase):

    def _format_step(self, step):
        step_stack = []
        _collect_steps(step_stack, step)
        return "\n".join(step_stack)

    def _assert_step_contains(self, step, name):
        if not _step_exists(step, name):
            steps = self._format_step(step)
            self.fail(f"{name} not contained in stack:\n{steps}")

    def _assert_step_not_contains(self, step, name):
        if _step_exists(step, name):
            steps = self._format_step(step)
            self.fail(f"unexpected step {name} found in stack:\n{steps}")

    def _assert_step_contains_all(self, step, names):
        for name in names:
            self._assert_step_contains(step, name)

    def test_build_defaults(self):
        """cmake build step should be default when not specified and toolchain exists"""
        p = Project(**_test_proj_config.copy())
        mock_env = mock.Mock(name='MockEnv')
        steps = p.build(mock_env)

        s = _fuzzy_find_step(steps, 'cmake build')
        self.assertIsNotNone(s)

    def test_override_build_steps(self):
        """explict build steps take precedence"""
        config = _test_proj_config.copy()
        config['build_steps'] = ['foo']
        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv')
        steps = p.build(mock_env)
        s = _fuzzy_find_step(steps, 'foo')
        self.assertIsNotNone(s)

    def test_upstream_builds_first(self):
        """upstream dependencies should be built first"""
        config = _test_proj_config.copy()
        config['upstream'] = [
            {'name': 'lib-1'}
        ]

        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv', config=config)
        steps = p.pre_build(mock_env)
        self._assert_step_contains_all(
            steps, ['build dependencies', 'build lib-1'])

    def test_extend_upstream_pre_post_build(self):
        """upstream dependency pre/post build can be extended from root project"""
        config = _test_proj_config.copy()
        config['upstream'] = [
            {
                'name': 'lib-1',
                'pre_build_steps': ['root pre-build'],
                'post_build_steps': ['root post-build']
            }
        ]

        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv', config=config)
        steps = p.pre_build(mock_env)
        self._assert_step_contains_all(
            steps, ['root pre-build', 'build lib-1', 'root post-build'])

    def test_default_test_step(self):
        """downstream tests should build by default"""
        config = _test_proj_config.copy()
        p = Project(**config)
        m_toolchain = mock.Mock(name='mock toolchain', cross_compile=False)
        mock_env = mock.Mock(name='MockEnv', config=config,
                             toolchain=m_toolchain)
        steps = p.test(mock_env)
        self._assert_step_contains(steps, 'test')

    def test_downstream_tests_build_by_default(self):
        """downstream tests should build by default"""

        config = _test_proj_config.copy()
        config['downstream'] = [
            {
                'name': 'lib-1'
            }
        ]

        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv', config=config)
        steps = p.build_consumers(mock_env)
        self._assert_step_contains_all(steps, ['test lib-1'])

    def test_downstream_tests_do_not_build(self):
        """downstream tests should not be built if requested"""

        config = _test_proj_config.copy()
        config['downstream'] = [
            {
                'name': 'lib-1',
                'run_tests': False
            }
        ]

        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv', config=config)
        steps = p.build_consumers(mock_env)
        self._assert_step_not_contains(steps, 'test lib-1')
