import unittest
import builder.core.util as utils


class TestUtils(unittest.TestCase):

    def test_deep_get_dict(self):
        """test deep_get for dictionary types"""
        d = {
            'foo': {
                'bar': {
                    'baz': 'quux'
                }
            }
        }

        self.assertEqual('quux', utils.deep_get(d, 'foo.bar.baz'))
        self.assertEqual(None, utils.deep_get(d, 'foo.bar.qux'))

    def test_deep_get_attr(self):
        """test deep_get for object attributes"""

        class Foo():
            pass

        obj = Foo()
        obj.foo = Foo()
        obj.foo.bar = Foo()
        obj.foo.bar.baz = 'quux'

        self.assertEqual('quux', utils.deep_get(obj, 'foo.bar.baz'))
        self.assertEqual(None, utils.deep_get(obj, 'foo.bar.qux'))

    def test_replace_variables(self):
        variables = {'x': 'foo', 'y': 'baz'}

        # string
        self.assertEqual("foo", utils.replace_variables("{x}", variables))
        self.assertEqual("foo.bar.baz", utils.replace_variables(
            "{x}.bar.{y}", variables))

        # lists
        self.assertEqual(["foo", "qux", "baz"], utils.replace_variables(
            ["{x}", "qux", "{y}"], variables))

        # dict
        value = {"f": "{x}", "x": "qux", "b": "{y}"}
        expected = {"f": "foo", "x": "qux", "b": "baz"}
        self.assertEqual(expected, utils.replace_variables(value, variables))

    def test_list_unique(self):
        expected = [1, 2, 3]
        self.assertEqual(expected, utils.list_unique([1, 1, 2, 1, 3, 2, 1, 3]))

    def test_tree_transform(self):
        tree = {
            'foo': {
                'bar': {
                    'baz': 2
                }
            },
            'baz': 2
        }

        def fn(x): return x * 2
        utils.tree_transform(tree, 'qux', fn)
        self.assertEqual(tree, tree)

        utils.tree_transform(tree, 'baz', fn)
        self.assertEqual(tree['baz'], 4)
        self.assertEqual(tree['foo']['bar']['baz'], 4)
