import os
import ssl
import unittest

import certifi
from slack import WebClient
from slack.errors import SlackApiError

from src.fetch.transfer_file import post_to_slack


class TestSlackPost(unittest.TestCase):
    def test_post_to_slack(self):
        # Test Results here:
        # https://cowservices.slack.com/archives/C03PW4CR38A/p1658933310842469
        bad_client = WebClient(
            token="",  # Invalid Token,
            ssl=ssl.create_default_context(cafile=certifi.where()),
        )
        good_client = WebClient(
            token=os.environ["SLACK_TOKEN"],
            ssl=ssl.create_default_context(cafile=certifi.where()),
        )
        with self.assertRaises(SlackApiError):
            post_to_slack(
                slack_client=bad_client,
                channel=os.environ["SLACK_CHANNEL"],
                message="",
                sub_messages={},
            )

        # TODO - delete these posts (i.e. cleanup)
        self.assertEqual(
            post_to_slack(
                slack_client=good_client,
                channel=os.environ["SLACK_CHANNEL"],
                message="Test Message",
                sub_messages={
                    "Test Category 1": "First Inner Message",
                    "Test Category 2": "Second Inner Message",
                },
            ),
            None,
        )


if __name__ == "__main__":
    unittest.main()
