import unittest


class TestFoo(unittest.TestCase):
    def test_perform(self):
        self.assertEqual(1, 1)

if __name__ == '__main__':
    unittest.main()
