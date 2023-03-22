"""
Basic Script to Extract the Extended Payment DataFrame for Solver Batch Rewards for a Block Range
"""

import argparse
import os
from datetime import timedelta, datetime

from src.constants import FILE_OUT_DIR
from src.fetch.payouts import extend_payment_df, TokenConversion
from src.fetch.prices import eth_in_token, token_in_eth, TokenId
from src.pg_client import MultiInstanceDBFetcher

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Get Payment Dataframe for block range (uses yesterday's prices)"
    )
    parser.add_argument(
        "--start",
        type=str,
        help="Start Block Number (block_deadline)",
        default="16865181",
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End Block Number (block_deadline)",
        default="999999999",
    )
    args = parser.parse_args()

    orderbook = MultiInstanceDBFetcher(
        db_urls=[os.environ["PROD_DB_URL"], os.environ["BARN_DB_URL"]]
    )

    yesterday = datetime.today() - timedelta(days=1)
    yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)

    start, end = args.start, args.end

    payment_df = extend_payment_df(
        pdf=orderbook.get_solver_rewards(start, end),
        # provide token conversion functions (ETH <--> COW)
        converter=TokenConversion(
            eth_to_token=lambda t: eth_in_token(TokenId.COW, t, yesterday),
            token_to_eth=lambda t: token_in_eth(TokenId.COW, t, yesterday),
        ),
    )
    out_path = FILE_OUT_DIR / f"payments-{start}-{end}-{yesterday.date()}.csv"
    payment_df.to_csv(out_path, index=False)
