"""
Basic Slack Post functionality. Sends a message thread to a specified channel.
"""
from slack.web.client import WebClient
from slack.web.slack_response import SlackResponse


def post_to_slack(
    slack_client: WebClient, channel: str, message: str, sub_messages: dict[str, str]
) -> None:
    """Posts message to Slack channel and sub message inside thread of first message"""
    response = slack_client.chat_postMessage(
        channel=channel,
        text=message,
        # Do not show link preview!
        # https://api.slack.com/reference/messaging/link-unfurling
        unfurl_media=False,
    )
    # This assertion is only for type safety,
    # since previous function can also return a Future
    assert isinstance(response, SlackResponse)
    # Post logs in thread.
    for category, log in sub_messages.items():
        slack_client.chat_postMessage(
            channel=channel,
            format="mrkdwn",
            text=f"{category}:\n```{log}```",
            # According to https://api.slack.com/methods/conversations.replies
            thread_ts=response.get("ts"),
            unfurl_media=False,
        )
