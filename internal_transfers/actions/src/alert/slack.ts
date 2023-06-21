import axios from "axios";
export async function alertSlack(slackWebhook: string, message: string) {
  const { data } = await axios.post(
    slackWebhook,
    { text: message },
    {
      headers: {
        "Content-Type": "application/json",
      },
    }
  );
  console.log(`Slack webhook response: ${data}`);
}
