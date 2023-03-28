import { getSettlementCompetitionData } from "../src/orderbook";

describe("getSettlementCompetitionData(txHash)", () => {
  test("Successful Fetch of Competition Data", async () => {
    expect(
      await getSettlementCompetitionData(
        "0x22bfb44e689e14e5b7b6d1ee7cb5fc2eb9e0db87f8fb54cc2baffc7ea17babdf"
      )
    ).toMatchSnapshot();
  });

  test("Successful Fetch of Competition Data (not internalized)", async () => {
    expect(
      await getSettlementCompetitionData(
        "0xf1df7c1d068c2e0f0cf324bb0739a838fff89b4b08bf2aa11a7b4a609a7e20fe"
      )
    ).toMatchSnapshot();
  });

  test("Fails to Fetch Barn Competition Data", async () => {
    expect(
      await getSettlementCompetitionData(
        "0xb45e23e7557094f1deed1b43bf229df4eef17b0dc7874241bbf1ed17ca21e4ae"
      )
    ).toMatchSnapshot();
  });

  test("Fails to Fetch invalid txHash", async () => {
    expect(await getSettlementCompetitionData("0x")).toBeUndefined();
  });
});
