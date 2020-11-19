
import unittest

from builder.core.vmod import VirtualModule


class MockVirtualModule(VirtualModule):
    CONSTANT = 42

    class A:
        pass

    class B:
        pass

    def function(x):
        return x


class TestVirtualModule(unittest.TestCase):

    def test_constant(self):
        from MockVirtualModule import CONSTANT
        self.assertEqual(CONSTANT, 42)

    def test_classes(self):
        from MockVirtualModule import A, B
        a = A()
        b = B()
        self.assertNotEqual(a.__class__, b.__class__)

    def test_function(self):
        from MockVirtualModule import CONSTANT, function
        self.assertEqual(42, function(CONSTANT))
