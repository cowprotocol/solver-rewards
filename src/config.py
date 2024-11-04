"""Config for solver accounting."""

import os
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from eth_typing.evm import ChecksumAddress
from dotenv import load_dotenv
from dune_client.types import Address
from gnosis.eth.ethereum_network import EthereumNetwork
from web3 import Web3

load_dotenv()


@dataclass(frozen=True)
class RewardConfig:
    """Configuration for reward mechanism."""

    reward_token_address: Address
    cow_bonding_pool: Address
    batch_reward_cap_upper: int
    batch_reward_cap_lower: int
    quote_reward_cow: int
    quote_reward_cap_native: int
    service_fee_factor: Fraction


@dataclass(frozen=True)
class ProtocolFeeConfig:
    """Configuration for protocol and parner fees."""

    protocol_fee_safe: Address
    partner_fee_cut: float
    partner_fee_reduced_cut: float
    reduced_cut_address: str


@dataclass(frozen=True)
class BufferAccountingConfig:
    """Configuration for buffer accounting."""

    include_slippage: bool


@dataclass(frozen=True)
class OrderbookConfig:
    """Configuration for orderbook fetcher"""

    prod_db_url: str
    barn_db_url: str


@dataclass(frozen=True)
class DuneConfig:
    """Configuration for DuneFetcher."""

    dune_api_key: str
    dune_blockchain: str


@dataclass(frozen=True)
class NodeConfig:
    """Configuration for web3 node."""

    node_url: str


@dataclass(frozen=True)
class PaymentConfig:
    """Configuration of payment."""

    # pylint: disable=too-many-instance-attributes

    network: EthereumNetwork
    cow_token_address: Address
    payment_safe_address: ChecksumAddress
    signing_key: str | None
    safe_queue_url: str
    csv_airdrop_url: str
    verification_docs_url: str
    weth_address: ChecksumAddress


@dataclass(frozen=True)
class IOConfig:
    """Configuration of input and output."""

    log_config_file: Path
    project_root_dir: Path
    query_dir: Path
    csv_output_dir: Path
    dashboard_dir: Path
    slack_channel: str | None
    slack_token: str | None


@dataclass(frozen=True)
class AccountingConfig:
    """Full configuration for solver accounting."""

    # pylint: disable=too-many-instance-attributes

    payment_config: PaymentConfig
    orderbook_config: OrderbookConfig
    dune_config: DuneConfig
    node_config: NodeConfig
    reward_config: RewardConfig
    protocol_fee_config: ProtocolFeeConfig
    buffer_accounting_config: BufferAccountingConfig
    io_config: IOConfig


def get_accounting_config(network: str) -> AccountingConfig:
    """Get config for specified network."""

    # pylint: disable=too-many-locals

    project_root_dir = Path(__file__).parent.parent
    file_out_dir = project_root_dir / Path("out")
    log_config_file = project_root_dir / Path("logging.conf")
    query_dir = project_root_dir / Path("queries")
    dashboard_dir = project_root_dir / Path("dashboards/solver-rewards-accounting")

    docs_url = "https://www.notion.so/cownation/Solver-Payouts-3dfee64eb3d449ed8157a652cc817a8c"

    payment_safe_address = Web3.to_checksum_address(
        os.environ.get("SAFE_ADDRESS", "0xA03be496e67Ec29bC62F01a428683D7F9c204930")
    )
    # Found this exposed infura key on https://rpc.info/
    infura_key = os.environ.get("INFURA_KEY", "9aa3d95b3bc440fa88ea12eaa4456161")

    node_url = f"https://{network}.infura.io/v3/{infura_key}"

    short_name = {
        "mainnet": "eth",
        "rinkeby": "rin",
        "gnosis": "gno",
        "goerli": "gor",
    }[network]

    csv_app_hash = "Qme49gESuwpSvwANmEqo34yfCkzyQehooJ5yL7aHmKJnpZ"
    safe_url = f"https://app.safe.global/{short_name}:{payment_safe_address}"
    airdrop_url = (
        f"{safe_url}/apps?appUrl=https://cloudflare-ipfs.com/ipfs/{csv_app_hash}/"
    )
    safe_queue_url = f"{safe_url}/transactions/queue"

    dune_api_key = os.environ["DUNE_API_KEY"]
    signing_key = os.getenv("PROPOSER_PK")
    if signing_key == "":
        signing_key = None
    result = AccountingConfig(
        payment_config=PaymentConfig(
            network=EthereumNetwork.MAINNET,
            cow_token_address=Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"),
            payment_safe_address=Web3.to_checksum_address(
                "0xA03be496e67Ec29bC62F01a428683D7F9c204930"
            ),
            signing_key=signing_key,
            safe_queue_url=safe_queue_url,
            csv_airdrop_url=airdrop_url,
            verification_docs_url=docs_url,
            weth_address=Web3.to_checksum_address(
                "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
            ),
        ),
        orderbook_config=OrderbookConfig(
            prod_db_url=os.environ["PROD_DB_URL"],
            barn_db_url=os.environ["BARN_DB_URL"],
        ),
        dune_config=DuneConfig(dune_api_key=dune_api_key, dune_blockchain="ethereum"),
        node_config=NodeConfig(node_url=node_url),
        reward_config=RewardConfig(
            reward_token_address=Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"),
            batch_reward_cap_upper=12 * 10**15,
            batch_reward_cap_lower=10 * 10**15,
            quote_reward_cow=6 * 10**18,
            quote_reward_cap_native=6 * 10**14,
            service_fee_factor=Fraction(15, 100),
            cow_bonding_pool=Address("0x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6"),
        ),
        protocol_fee_config=ProtocolFeeConfig(
            protocol_fee_safe=Address("0xB64963f95215FDe6510657e719bd832BB8bb941B"),
            partner_fee_cut=0.15,
            partner_fee_reduced_cut=0.10,
            reduced_cut_address="0x63695Eee2c3141BDE314C5a6f89B98E62808d716",
        ),
        buffer_accounting_config=BufferAccountingConfig(include_slippage=True),
        io_config=IOConfig(
            project_root_dir=project_root_dir,
            log_config_file=log_config_file,
            query_dir=query_dir,
            csv_output_dir=file_out_dir,
            dashboard_dir=dashboard_dir,
            slack_channel=os.getenv("SLACK_CHANNEL", None),
            slack_token=os.getenv("SLACK_TOKEN", None),
        ),
    )

    return result


config = get_accounting_config(os.environ["NETWORK"])

web3 = Web3(Web3.HTTPProvider(config.node_config.node_url))
