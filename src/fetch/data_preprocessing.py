"""Preprocessing of data for payments
The processing in this file should be minimal, mostly to correct for incorrect price data or to
exclude trades from accounting.
Any processing which is not required anymore should be removed.
If this file contains any processing, the accounting period should be added in the description,
with a short description of the processing."""

from pandas import DataFrame


def preprocess_batch_data(batch_data_df: DataFrame) -> DataFrame:
    """Preprocess batch data"""
    return batch_data_df


def preprocess_trade_data(trade_data_df: DataFrame) -> DataFrame:
    """Preprocess trade data
    Accounting period starting on: 2024-05-07
    This processing corrects prices of FXN token which was off until the middle of the accounting period. The price 35322822331170980 was the last price before it became
    unreasonably large (due to an out of sync $0.02 TVL Uniswap pool).
    """
    trade_data_df.loc[
        (trade_data_df["buy_token"] == "0x365accfca291e7d3914637abf1f7635db165bb09")
        & (trade_data_df["buy_token_native_price"] > 1e18),
        "buy_token_native_price",
    ] = 35322822331170980.0
    trade_data_df.loc[
        (trade_data_df["sell_token"] == "0x365accfca291e7d3914637abf1f7635db165bb09")
        & (trade_data_df["sell_token_native_price"] > 1e18),
        "sell_token_native_price",
    ] = 35322822331170980.0
    return trade_data_df


def preprocess_slippage_data(slippage_data: DataFrame) -> DataFrame:
    """Preprocess slippage data"""
    return slippage_data


def preprocess_reward_target(reward_target_df: DataFrame) -> DataFrame:
    """Preprocess reward targets"""
    return reward_target_df
