import { APIGatewayEvent, APIGatewayProxyResult } from "aws-lambda";
import { Context as AwsContext } from "aws-lambda/handler";
import { txHandler } from "./src/pipeline";
import { Buffer } from "buffer";

const decode = (str: string): string =>
  Buffer.from(str, "base64").toString("binary");

export const handler = async (
  event: APIGatewayEvent,
  _context: AwsContext
): Promise<APIGatewayProxyResult> => {
  const secrets = {
    nodeUrl: process.env.NODE_URL!,
    dbUrl: process.env.DATABASE_URL!,
    simulatorKey: process.env.TENDERLY_ACCESS_KEY!,
  };
  let txHash: string;
  if (event.body !== null) {
    txHash = JSON.parse(decode(event.body)).txHash;
  } else {
    txHash = (event as any).txHash;
  }

  await txHandler(txHash, secrets);
  return {
    statusCode: 200,
    body: JSON.stringify({
      message: `Processed TxHash ${txHash}`,
    }),
  };
};
