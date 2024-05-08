"""Functionality for computing fees

The two main functions used in other parts of the code are 
- `compute_trade_fees` for computing fees for individual trades and 
- `compute_protocol_partner_fees` for constructing aggregate data on protocol fees and
  partner fees."""

import json
import binascii
from fractions import Fraction

import pandas
from pandas import DataFrame, Series
from dune_client.types import Address

from src.fetch.prices import TokenConversion

PROTOCOL_FEE_SAFE = Address("0xB64963f95215FDe6510657e719bd832BB8bb941B")
PARTNER_FEE_CUT = 0.15


def compute_trade_fees(trade_data_df: DataFrame) -> DataFrame:
    """Compute fees for individual trades
    The input dataframe `trade_data_df` containd data on trades. This function creates a new
    dataframe with information on protocol fees, partner fees, and network fees, by applying
    the function `compute_trade_fee_datum` to every row.
    """
    trade_fees_df = (
        trade_data_df.apply(compute_trade_fee_datum, axis=1, result_type="expand")
        .rename(
            columns={
                0: "auction_id",
                1: "order_uid",
                2: "winning_solver",
                3: "network_fee",
                4: "protocol_fees",
                5: "protocol_fee_tokens",
                6: "protocol_fee_token_native_prices",
                7: "protocol_fee_kinds",
                8: "is_partner_fee",
                9: "recipient",
            }
        )
        .astype(object)
    )
    return trade_fees_df


def compute_trade_fee_datum(
    row: Series,
) -> tuple[
    int,
    str,
    str,
    int,
    list[int],
    list[str],
    list[float],
    list[str],
    list[bool],
    str | None,
]:
    """Compute protocol for a given order
    It loops through all protocol fees attached to an order, computes individual protocol
    fees, updates executed amount as they would have been without a protocol fee, and
    computes the network fee set by solvers.
    Functions for computing individual protocol fees, e.g. `compute_surplus_protocol_fee`,
    need to take inputs of the form
    (row, sell_amount, buy_amount, *protocol_fee_parameters)
    and output
    (protocol_fee, Protocol_fee_token, protocol_fee_token_native_price,
     sell_amount_before_fees, buy_amount_before_fees)"""
    # pylint: disable-msg=too-many-locals
    protocol_fees: list[int] = []
    protocol_fee_tokens: list[str] = []
    protocol_fee_token_native_prices: list[float] = []
    protocol_fee_kinds: list[str] = []

    if row["protocol_fee_kind"] is None:
        return (
            int(row["auction_id"]),
            str(row["order_uid"]),
            str(row["winning_solver"]),
            int(row["observed_fee"] * row["sell_token_native_price"] / 10**18),
            protocol_fees,
            protocol_fee_tokens,
            protocol_fee_token_native_prices,
            protocol_fee_kinds,
            [],
            None,
        )

    recipient = parse_recipient(row)

    protocol_fee_kind_list = parse_protocol_fee_kind(row)

    # if there is a recipient, the last fee becomes a partner fee
    is_partner_fee = [False for _ in protocol_fee_kind_list]
    if recipient is not None:
        if protocol_fee_kind_list[-1] == "volume":
            is_partner_fee[-1] = True
        else:
            raise ValueError(
                'Partner fee recipient set but last fee policy is not of kind "volume"'
                f'but "{protocol_fee_kind_list[-1]}".'
            )

    # loop over protocol fees and update executed amounts as if there were no fees
    executed_sell_amount = row["sell_amount"]
    executed_buy_amount = row["buy_amount"]

    # iterate over fees in reverse order
    sorted_protocol_fee_data = sorted(
        zip(
            row["application_order"],
            protocol_fee_kind_list,
            row["surplus_factor"],
            row["surplus_max_volume_factor"],
            row["volume_factor"],
            row["price_improvement_factor"],
            row["price_improvement_max_volume_factor"],
        ),
        reverse=True,
    )
    for (
        _,
        protocol_fee_kind,
        surplus_factor,
        surplus_max_volume_factor,
        volume_factor,
        price_improvement_factor,
        price_improvement_max_volume_factor,
    ) in sorted_protocol_fee_data:
        if protocol_fee_kind == "surplus":
            (
                protocol_fee,
                protocol_fee_token,
                protocol_fee_token_native_price,
                executed_sell_amount,
                executed_buy_amount,
            ) = compute_surplus_protocol_fee(
                row,
                executed_sell_amount,
                executed_buy_amount,
                surplus_factor,
                surplus_max_volume_factor,
            )
        elif protocol_fee_kind == "priceimprovement":
            (
                protocol_fee,
                protocol_fee_token,
                protocol_fee_token_native_price,
                executed_sell_amount,
                executed_buy_amount,
            ) = compute_price_improvement_protocol_fee(
                row,
                executed_sell_amount,
                executed_buy_amount,
                price_improvement_factor,
                price_improvement_max_volume_factor,
            )

        elif protocol_fee_kind == "volume":
            (
                protocol_fee,
                protocol_fee_token,
                protocol_fee_token_native_price,
                executed_sell_amount,
                executed_buy_amount,
            ) = compute_volume_protocol_fee(
                row,
                executed_sell_amount,
                executed_buy_amount,
                volume_factor,
            )

        else:
            raise ValueError(
                f"Unknow protocol fee kind \"{row['kind']}\"."
                'Only "surplus", "priceimprovement", and "volume" are supported.'
            )

        protocol_fees.append(protocol_fee)
        protocol_fee_tokens.append(protocol_fee_token)
        protocol_fee_token_native_prices.append(protocol_fee_token_native_price)
        protocol_fee_kinds.append(protocol_fee_kind)

    network_fee = compute_network_fee(row, executed_sell_amount, executed_buy_amount)

    return (
        int(row["auction_id"]),
        str(row["order_uid"]),
        str(row["winning_solver"]),
        network_fee,
        protocol_fees[::-1],
        protocol_fee_tokens[::-1],
        protocol_fee_token_native_prices[::-1],
        protocol_fee_kinds[::-1],
        is_partner_fee,
        recipient,
    )


def compute_surplus_protocol_fee(
    row: Series,
    sell_amount: int,
    buy_amount: int,
    surplus_factor: float,
    surplus_max_volume_factor: float,
) -> tuple[int, str, float, int, int]:
    """Compute the surplus protocol fee"""
    sell_amount_before_fee = sell_amount
    buy_amount_before_fee = buy_amount
    if row["kind"] == "sell":
        surplus = buy_amount - int(
            sell_amount
            * Fraction(int(row["limit_buy_amount"]), int(row["limit_sell_amount"]))
        )
        surplus_fee = int(surplus_factor / (1 - surplus_factor) * surplus)

        volume = buy_amount
        volume_fee = int(
            surplus_max_volume_factor / (1 - surplus_max_volume_factor) * volume
        )

        protocol_fee = min(surplus_fee, volume_fee)
        protocol_fee_token = row["buy_token"]
        protocol_fee_token_native_price = row["buy_token_native_price"] / 10**18

        buy_amount_before_fee += protocol_fee
    elif row["kind"] == "buy":
        volume = sell_amount
        surplus = (
            int(
                buy_amount
                * Fraction(int(row["limit_sell_amount"]), int(row["limit_buy_amount"]))
            )
            - sell_amount
        )
        surplus_fee = int(surplus_factor / (1 - surplus_factor) * surplus)

        volume = sell_amount
        volume_fee = int(
            surplus_max_volume_factor / (1 + surplus_max_volume_factor) * volume
        )

        protocol_fee = min(surplus_fee, volume_fee)
        protocol_fee_token = row["sell_token"]
        protocol_fee_token_native_price = row["sell_token_native_price"] / 10**18

        sell_amount_before_fee -= protocol_fee
    else:
        raise ValueError(
            f"Unknow order kind \"{row['kind']}\". Only \"sell\" and \"buy\" are supported."
        )

    return (
        protocol_fee,
        protocol_fee_token,
        protocol_fee_token_native_price,
        sell_amount_before_fee,
        buy_amount_before_fee,
    )


def compute_price_improvement_protocol_fee(
    row: Series,
    sell_amount: int,
    buy_amount: int,
    price_improvement_factor: float,
    price_improvement_max_volume_factor: float,
) -> tuple[int, str, float, int, int]:
    """Compute the price improvement protocol fee"""
    sell_amount_before_fee = sell_amount
    buy_amount_before_fee = buy_amount
    if row["kind"] == "sell":
        price_improvement = buy_amount - int(
            sell_amount
            * Fraction(
                int(
                    row["quote_buy_amount"]
                    - row["quote_buy_amount"]
                    / row["quote_sell_amount"]
                    * row["quote_gas_amount"]
                    * row["quote_gas_price"]
                    / row["quote_sell_token_price"]
                ),
                int(row["quote_sell_amount"]),
            )
        )
        price_improvement_fee = int(
            price_improvement_factor
            / (1 - price_improvement_factor)
            * price_improvement
        )

        volume = buy_amount
        volume_fee = int(
            price_improvement_max_volume_factor
            / (1 - price_improvement_max_volume_factor)
            * volume
        )

        protocol_fee = max(0, min(price_improvement_fee, volume_fee))
        protocol_fee_token = row["buy_token"]
        protocol_fee_token_native_price = row["buy_token_native_price"] / 10**18

        buy_amount_before_fee += protocol_fee
    elif row["kind"] == "buy":
        price_improvement = int(
            buy_amount
            * Fraction(
                int(
                    row["quote_sell_amount"]
                    + row["quote_gas_amount"]
                    * row["quote_gas_price"]
                    / row["quote_sell_token_price"]
                ),
                int(row["quote_buy_amount"]),
            )
            - sell_amount
        )
        price_improvement_fee = int(
            price_improvement_factor
            / (1 - price_improvement_factor)
            * price_improvement
        )

        volume = sell_amount
        volume_fee = int(
            price_improvement_max_volume_factor
            / (1 + price_improvement_max_volume_factor)
            * volume
        )

        protocol_fee = max(0, min(price_improvement_fee, volume_fee))
        protocol_fee_token = row["sell_token"]
        protocol_fee_token_native_price = row["sell_token_native_price"] / 10**18

        sell_amount_before_fee -= protocol_fee
    else:
        raise ValueError(
            f"Unknow order kind \"{row['kind']}\". Only \"sell\" and \"buy\" are supported."
        )

    return (
        protocol_fee,
        protocol_fee_token,
        protocol_fee_token_native_price,
        sell_amount_before_fee,
        buy_amount_before_fee,
    )


def compute_volume_protocol_fee(
    row: Series,
    sell_amount: int,
    buy_amount: int,
    volume_factor: float,
) -> tuple[int, str, float, int, int]:
    """Compute the volume protocol fee"""
    sell_amount_before_fee = sell_amount
    buy_amount_before_fee = buy_amount
    if row["kind"] == "sell":
        volume = buy_amount
        protocol_fee = int(volume_factor / (1 - volume_factor) * volume)
        protocol_fee_token = row["buy_token"]
        protocol_fee_token_native_price = row["buy_token_native_price"] / 10**18
        buy_amount_before_fee += protocol_fee
    elif row["kind"] == "buy":
        volume = sell_amount
        protocol_fee = int(volume_factor / (1 + volume_factor) * volume)
        protocol_fee_token = row["sell_token"]
        protocol_fee_token_native_price = row["sell_token_native_price"] / 10**18
        sell_amount_before_fee -= protocol_fee
    else:
        raise ValueError(
            f"Unknow order kind \"{row['kind']}\". Only \"sell\" and \"buy\" are supported."
        )
    return (
        protocol_fee,
        protocol_fee_token,
        protocol_fee_token_native_price,
        sell_amount_before_fee,
        buy_amount_before_fee,
    )


def compute_network_fee(
    row: Series, sell_amount_before_fee: int, buy_amount_before_fee: int
) -> int:
    """Compute network fees of an order in the sell token
    It uses the fact that
    (sell_amount_before_fee - network_fee) / buy_amount_before_fee =
    (sell_amount - observed_fee) / buy_amount)
    with sell_amount_before_fee and buy_amount_before_fee being the amount before applying
    any **protocol** fees and sell_amount and buy_amount beeing the executed values on chain.
    """
    network_fee = int(
        (
            sell_amount_before_fee
            - buy_amount_before_fee
            * Fraction(
                int(row["sell_amount"] - row["observed_fee"]), int(row["buy_amount"])
            )
        )
        * row["sell_token_native_price"]
        / 10**18
    )
    return network_fee


def parse_recipient(row: Series) -> str | None:
    """Parse partner fee recipient from app data
    If there is no parter fee recipoient or if the parsing of app data fails for any reason,
    the function returns `None`.
    """
    try:
        return json.loads(binascii.unhexlify(row["app_data"][2:]).decode("utf-8"))[
            "metadata"
        ]["partnerFee"]["recipient"]
    except (KeyError, json.decoder.JSONDecodeError):
        return None


def parse_protocol_fee_kind(row: Series) -> list[str]:
    """Parse protocol fee kind
    Parses the string returned by the SQL query into a list of strings.
    """
    return row["protocol_fee_kind"].strip("{}").split(",")


def compute_protocol_partner_fees(
    trade_fees_df: DataFrame, converter: TokenConversion
) -> DataFrame:
    """Compute aggreage protocol fee data per recipient
    Partner fees are already reduced by 15% and the sum over all 15% cuts is aggregated into
    one row.

    The result has the columns "recipient", "fee_eth", "fee_cow" (currently not used), and
    "from_partner_fee" (`True` for partner fee transfers and the transfer for the 15% cut,
    `False` for the transfoer of protocol fees).
    """
    # split into protocol and partner fees
    trade_total_fees_df = (
        trade_fees_df.apply(compute_total_fees, axis=1, result_type="expand")
        .rename(
            columns={
                0: "auction_id",
                1: "order_uid",
                2: "winning_solver",
                3: "recipient",
                4: "protocol_fee",
                5: "partner_fee_tax",
                6: "partner_fee",
            }
        )
        .astype(object)
    )

    # combine into final protocol and partner fee DataFrame
    protocol_partner_fees_df = (
        trade_total_fees_df.groupby("recipient")
        .partner_fee.sum()
        .reset_index()
        .rename(columns={"partner_fee": "fee_eth"})
        .astype(object)
        .sort_values("recipient")
    )
    protocol_partner_fees_df["from_partner_fee"] = True
    protocol_partner_fees_df = pandas.concat(
        [
            DataFrame(
                [
                    {
                        "recipient": str(PROTOCOL_FEE_SAFE),
                        "fee_eth": trade_total_fees_df.protocol_fee.sum(),
                        "from_partner_fee": False,
                    },
                    {
                        "recipient": str(PROTOCOL_FEE_SAFE),
                        "fee_eth": trade_total_fees_df.partner_fee_tax.sum(),
                        "from_partner_fee": True,
                    },
                ]
            ),
            protocol_partner_fees_df,
        ],
        ignore_index=True,
    ).astype(object)
    protocol_partner_fees_df["fee_cow"] = (
        protocol_partner_fees_df["fee_eth"].apply(converter.eth_to_token).astype(object)
    )

    return protocol_partner_fees_df


def compute_total_fees(row: Series) -> tuple[int, str, str, str, int, int, int]:
    """Aggregate fees of a trade
    Besides trade information, the result contains aggregate protocol fees, partner fee tax,
    and partnerfee.
    """
    trade_protocol_fee = 0
    trade_partner_fee_tax = 0
    trade_partner_fee = 0

    for (
        protocol_fee,
        protocol_fee_token_native_price,
        is_partner_fee,
    ) in zip(
        row["protocol_fees"],
        row["protocol_fee_token_native_prices"],
        row["is_partner_fee"],
    ):
        trade_protocol_fee += (
            protocol_fee * protocol_fee_token_native_price * (1 - is_partner_fee)
        )

        trade_partner_fee_tax += (
            protocol_fee
            * protocol_fee_token_native_price
            * is_partner_fee
            * PARTNER_FEE_CUT
        )
        trade_partner_fee += (
            protocol_fee
            * protocol_fee_token_native_price
            * is_partner_fee
            * (1 - PARTNER_FEE_CUT)
        )

    return (
        row["auction_id"],
        row["order_uid"],
        row["winning_solver"],
        row["recipient"],
        int(trade_protocol_fee),
        int(trade_partner_fee_tax),
        int(trade_partner_fee),
    )
