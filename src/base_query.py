from enum import Enum
from typing import Optional

from duneapi.types import DuneQuery, Network, QueryParameter
from duneapi.util import open_query

from src.models import AccountingPeriod

# pylint: disable=line-too-long
RECOGNIZED_BONDING_POOLS = [
    "('\\x8353713b6D2F728Ed763a04B886B16aAD2b16eBD'::bytea, 'Gnosis', '\\x6c642cafcbd9d8383250bb25f67ae409147f78b2'::bytea)",
    "('\\x5d4020b9261F01B6f8a45db929704b0Ad6F5e9E6'::bytea, 'CoW Services', '\\x423cec87f19f0778f549846e0801ee267a917935'::bytea)",
]


class ConnectionType(Enum):
    LOCAL = "local"
    REMOTE = "remote"


def base_query(
    name: str,
    period: AccountingPeriod,
    select: str,
    connection_type: ConnectionType = ConnectionType.REMOTE,
    bonding_pools: Optional[list[str]] = None,
    tx_hash: Optional[str] = "0x",
    additional_parameters: Optional[list[QueryParameter]] = None,
) -> DuneQuery:
    if not bonding_pools:
        bonding_pools = RECOGNIZED_BONDING_POOLS
    parameters = [
        QueryParameter.date_type("StartTime", period.start),
        QueryParameter.date_type("EndTime", period.end),
        QueryParameter.text_type("BondingPoolData", ",\n  ".join(bonding_pools)),
        QueryParameter.text_type("TxHash", tx_hash),
    ]
    if additional_parameters:
        parameters += additional_parameters

    query = "\n".join([open_query("./queries/solver_slippage.sql"), select])
    if connection_type == ConnectionType.REMOTE:
        return DuneQuery.from_environment(
            # TODO - this field should be renamed to `query_template`.
            #  `raw_sql` should be constructed from template and parameters
            #  as in `fill_parameterized_query`. This is a task for duneapi:
            # https://github.com/bh2smith/duneapi/issues/46
            raw_sql=query,
            network=Network.MAINNET,
            name=name,
            parameters=parameters,
        )
    else:
        return DuneQuery(
            raw_sql=query,
            network=Network.MAINNET,
            name=name,
            parameters=parameters,
            description="",
            query_id=-1
        )
