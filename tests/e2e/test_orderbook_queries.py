import os
import unittest

import pandas as pd
from dotenv import load_dotenv

from src.pg_client import MultiInstanceDBFetcher


def participant_query(auction_id: int):
    return f"""
            select concat('0x', encode(participant, 'hex')) as solver 
            from auction_participants 
            where auction_id = {auction_id}
            order by participant
            """


def observation_query(block_number: int):
    return f"""
            select *
            from settlement_observations
            where block_number = {block_number}
            -- Technically we should include log_index 
            -- constraint but its unlikely to have two 
            -- settlements in the same block
            --  and log_index = 263;
            """


def score_query(auction_id: int):
    return f"""
            select *
            from settlement_scores
            where auction_id = {auction_id};
            """


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        load_dotenv()
        self.fetcher = MultiInstanceDBFetcher([os.environ["BARN_DB_URL"]])
        self.query_engine = self.fetcher.connections[0]

    def test_get_solver_rewards_16735008(self):
        """This is auction ID"""
        tx = "0x203bac6edde8f4dd2e18e7a5e2d81cb721d8b4f1f021217d0d4b55a799efe3f0"
        # TODO - should be able to link tx_hash, auction_id and settlement_block
        start, end = "16735007", "16735008"
        auction_id = 6999998
        settlement_block = 16734995

        # This is an example of negative clamping.
        block_deadline = 16735008
        fee = 0.0
        surplus = 53999674326241
        winning_score = 11761680942929144.0
        reference_score = 11761680942929126.0
        gas_used = 116738.0
        gas_price = 64572736497.0
        gas_cost = gas_used * gas_price
        winner = "0xde786877a10dbb7eba25a4da65aecf47654f08ab"

        expected_observations = self.fetcher.exec_query(
            observation_query(settlement_block), self.query_engine
        )

        self.assertIsNone(
            pd.testing.assert_frame_equal(
                expected_observations,
                pd.DataFrame(
                    {
                        "block_number": [settlement_block],
                        "log_index": [263],
                        "gas_used": [gas_used],
                        "effective_gas_price": [gas_price],
                        "surplus": [surplus],
                        "fee": [fee],
                    }
                ),
            )
        )

        expected_score = self.fetcher.exec_query(
            score_query(auction_id), self.query_engine
        )

        self.assertIsNone(
            pd.testing.assert_frame_equal(
                expected_score,
                pd.DataFrame(
                    {
                        "auction_id": [auction_id],
                        "winner": [winner],
                        "winning_score": [winning_score],
                        "reference_score": [reference_score],
                        "block_deadline": [block_deadline],
                    }
                ),
            )
        )

        expected_participants = self.fetcher.exec_query(
            participant_query(auction_id), self.query_engine
        )["solver"]


        rewards = self.fetcher.get_solver_rewards(start, end)
        expected = pd.DataFrame(
            {
                "solver": [
                    "0x8a4e90e9afc809a69d2a3bdbe5fff17a12979609",
                    "0xde786877a10dbb7eba25a4da65aecf47654f08ab",
                    "0xe33062a24149f7801a48b2675ed5111d3278f0f5",
                ],
                "payment_eth": [0.0, -10000000000000000.0, 0.0],
                "execution_cost_eth": [0.0, gas_cost, 0.0],
                "num_participating_batches": [1, 1, 1],
            }
        )
        self.assertIsNone(
            pd.testing.assert_series_equal(rewards["solver"], expected_participants)
        )

        self.assertIsNone(pd.testing.assert_frame_equal(expected, rewards))


if __name__ == "__main__":
    unittest.main()
