
import unittest

from builder.core.toolchain import Toolchain


class ToolchainTest(unittest.TestCase):

    def test_all_compilers(self):
        toolchain = Toolchain()
        all_compilers = toolchain.all_compilers()
        self.assertGreaterEqual(len(all_compilers), 1)

    def test_default_compiler(self):
        toolchain = Toolchain()
        all_compilers = toolchain.all_compilers()
        default_compiler = toolchain.default_compiler()
        self.assertIn(default_compiler, all_compilers)
