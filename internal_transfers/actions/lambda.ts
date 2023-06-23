import { APIGatewayEvent, APIGatewayProxyResult } from "aws-lambda";
import { Context as AwsContext } from "aws-lambda/handler";
import { txHandler } from "./src/pipeline";

export const handler = async (
  event: APIGatewayEvent,
  _context: AwsContext
): Promise<APIGatewayProxyResult> => {
  const secrets = {
    nodeUrl: process.env.NODE_URL!,
    dbUrl: process.env.DATABASE_URL!,
    simulatorKey: process.env.TENDERLY_ACCESS_KEY!,
  };
  const txHash = event.body
    ? JSON.parse(event.body).txHash
    : (event as any).txHash;

  await txHandler(txHash, secrets);
  return {
    statusCode: 200,
    body: JSON.stringify({
      message: `Processed TxHash ${txHash}`,
    }),
  };
};
