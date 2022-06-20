import os
import unittest
import unittest.mock as mock

from builder.core.project import Project
from builder.core.spec import BuildSpec
from builder.actions.script import Script

import builder.core.api  # force API to load and expose the virtual module
here = os.path.dirname(os.path.abspath(__file__))

test_data_dir = os.path.join(here, 'data')

# base config -- copy for tests
_test_proj_config = {
    'name': 'test-proj',
    'search_dirs': [test_data_dir],
    'path': here,
}


def _collect_steps(step):
    """
    collect the list of steps
    """

    def _collect_steps_impl(out, curr):
        if isinstance(curr, list):
            for s in curr:
                _collect_steps_impl(out, s)
        elif isinstance(curr, Script):
            out.append(str(curr))
            _collect_steps_impl(out, curr.commands)
        else:
            out.append(str(curr))

    stack = []
    _collect_steps_impl(stack, step)
    return stack


def _fuzzy_find_step(step_stack, step, name):
    """
    attempt to find a step name or value that either matches name or contains name as a fragment
    :return: tuple(step, stack idx) | None
    """
    for i in range(len(step_stack)):
        s = step_stack[i]
        if s == name or name in s:
            return s, i
    return None


def _step_exists(step, name):
    """
    test if the step [name] exists in the set of [step]s
    """
    step_stack = _collect_steps(step)
    return _fuzzy_find_step(step_stack, step, name) is not None


def _dump_step(step):
    import pprint
    steps = _collect_steps(step)
    pprint.pprint(steps, width=240)


class TestProject(unittest.TestCase):

    def setUp(self):
        # remove possible inter test behavior
        Project._projects.clear()

    def _format_step(self, step):
        step_stack = _collect_steps(step)
        return "\n".join(step_stack)

    def _assert_step_contains(self, step, name):
        if not _step_exists(step, name):
            steps = self._format_step(step)
            self.fail(f"{name} not contained in stack:\n{steps}")

    def _assert_step_not_contains(self, step, name):
        if _step_exists(step, name):
            steps = self._format_step(step)
            self.fail(f"unexpected step {name} found in stack:\n{steps}")

    def _assert_step_contains_all(self, step, names, ordered=True):
        for name in names:
            self._assert_step_contains(step, name)

        if ordered:
            stack = _collect_steps(step)
            steps = [_fuzzy_find_step(stack, step, name) for name in names]
            step_indices = [t[1] for t in steps]
            steps_in_order = all(step_indices[i] <= step_indices[i+1] for i in range(len(step_indices) - 1))
            formatted_steps = self._format_step(step)
            self.assertTrue(
                steps_in_order, f"steps exist but not in order expected:\nexpected:{names}\nfound:\n{formatted_steps}")

    def test_build_defaults(self):
        """cmake build step should be default when not specified and toolchain exists"""
        p = Project(**_test_proj_config.copy())
        mock_env = mock.Mock(name='MockEnv')
        steps = p.build(mock_env)
        self._assert_step_contains(steps, 'cmake build')

    def test_override_build_steps(self):
        """explict build steps take precedence"""
        config = _test_proj_config.copy()
        config['build_steps'] = ['foo']
        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv')
        steps = p.build(mock_env)
        self._assert_step_contains(steps, 'foo')

    def test_upstream_builds_first(self):
        """upstream dependencies should be built first"""
        config = _test_proj_config.copy()
        config['upstream'] = [
            {'name': 'lib-1'}
        ]

        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv', config=config)
        mock_env.spec = BuildSpec()
        steps = p.pre_build(mock_env)
        self._assert_step_contains_all(steps, ['build dependencies', 'build lib-1'])

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
        mock_env.spec = BuildSpec()
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
        mock_env.spec = BuildSpec()
        steps = p.build_consumers(mock_env)
        self._assert_step_not_contains(steps, 'test lib-1')

    def test_downstream_post_build_runs_before_tests(self):
        """downstream post_build_steps should run before tests"""
        config = _test_proj_config.copy()
        config['downstream'] = [
            {
                'name': 'lib-1'
            }
        ]

        p = Project(**config)
        mock_env = mock.Mock(name='MockEnv', config=config)
        mock_env.spec = BuildSpec()
        steps = p.build_consumers(mock_env)
        self._assert_step_contains_all(steps, ['post build lib-1', 'test lib-1'])

    def test_explicit_upstream_branch(self):
        """upstream with specific revision should override the detected branch"""
        config = _test_proj_config.copy()
        config['upstream'] = [
            {
                'name': 'lib-1',
                'revision': 'explicit-branch'
            }
        ]

        p = Project(**config)
        spec = BuildSpec(target='linux')
        deps = p.get_dependencies(spec)
        self.assertEqual('explicit-branch', deps[0].revision)

    def test_upstream_targets_filtered_for_spec(self):
        """upstream with specific targets should only be applied if target matches current spec"""
        config = _test_proj_config.copy()
        config['upstream'] = [
            {
                'name': 'lib-1',
                'targets': ['linux']
            }
        ]

        p = Project(**config)
        spec = BuildSpec(target='macos')
        dependencies = p.get_dependencies(spec)
        self.assertEqual(0, len(dependencies), "dependencies should have filtered upstream with specific target")

    def test_project_source_dir_replaced(self):
        """project specific dependency variables should be replaced"""
        config = _test_proj_config.copy()
        config['upstream'] = [
            {
                'name': 'lib-1'
            }
        ]

        p = Project(**config)
        spec = BuildSpec(target='macos')
        dependencies = p.get_dependencies(spec)
        m_env = mock.Mock(name='MockEnv', config=config)
        steps = dependencies[0].post_build(m_env)
        self._assert_step_contains(steps, "{}/gradlew postBuildTask".format(os.path.join(test_data_dir, "lib-1")))
