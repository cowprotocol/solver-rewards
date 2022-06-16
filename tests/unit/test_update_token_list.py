import unittest

from duneapi.api import DuneAPI

from src.update.token_list import update_token_list


class TestTokenList(unittest.TestCase):

    def test_empty_token_list_update(self):
        dune = DuneAPI("user", "password")
        with self.assertRaises(ValueError) as err:
            update_token_list(dune, [])

        self.assertEqual(str(err.exception), "Can't update and empty token list")


if __name__ == "__main__":
    unittest.main()
