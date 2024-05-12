"""Preprocessing of data for payments
Accounting period starting on: 2024-04-30"""

from pandas import DataFrame


def preprocess_batch_data(batch_data_df: DataFrame) -> DataFrame:
    """Preprocess batch data"""
    return batch_data_df


def preprocess_trade_data(trade_data_df: DataFrame) -> DataFrame:
    """Preprocess trade data"""
    trade_data_df.loc[
        trade_data_df["buy_token"] == "0x365accfca291e7d3914637abf1f7635db165bb09",
        "buy_token_native_price",
    ] = 0.03532282233117098
    trade_data_df.loc[
        trade_data_df["sell_token"] == "0x365accfca291e7d3914637abf1f7635db165bb09",
        "sell_token_native_price",
    ] = 0.03532282233117098
    return trade_data_df


def preprocess_slippage_data(slippage_data: DataFrame) -> DataFrame:
    """Preprocess slippage data"""
    return slippage_data


def preprocess_reward_target(reward_target_df: DataFrame) -> DataFrame:
    """Preprocess reward targets"""
    return reward_target_df
