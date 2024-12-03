"""Config for solver accounting."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path

from eth_typing.evm import ChecksumAddress
from dotenv import load_dotenv
from dune_client.types import Address
from gnosis.eth.ethereum_network import EthereumNetwork
from web3 import Web3

load_dotenv()


class Network(Enum):
    """Network class for networks supported by the accounting."""

    MAINNET = "mainnet"
    GNOSIS = "gnosis"
    ARBITRUM_ONE = "arbitrum"
    BASE = "base"


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

    @staticmethod
    def from_network(network: Network) -> RewardConfig:
        """Initialize reward config for a given network."""
        cow_bonding_pool = Address("0x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6")
        service_fee_factor = Fraction(15, 100)
        match network:
            case Network.MAINNET:
                return RewardConfig(
                    reward_token_address=Address(
                        "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"
                    ),
                    batch_reward_cap_upper=12 * 10**15,
                    batch_reward_cap_lower=10 * 10**15,
                    quote_reward_cow=6 * 10**18,
                    quote_reward_cap_native=6 * 10**14,
                    service_fee_factor=service_fee_factor,
                    cow_bonding_pool=cow_bonding_pool,
                )
            case Network.GNOSIS:
                return RewardConfig(
                    reward_token_address=Address(
                        "0x177127622c4a00f3d409b75571e12cb3c8973d3c"
                    ),
                    batch_reward_cap_upper=30 * 10**18,
                    batch_reward_cap_lower=5 * 10**18,
                    quote_reward_cow=6 * 10**18,
                    quote_reward_cap_native=1 * 10**18,
                    service_fee_factor=service_fee_factor,
                    cow_bonding_pool=cow_bonding_pool,
                )
            case Network.ARBITRUM_ONE:
                return RewardConfig(
                    reward_token_address=Address(
                        "0xcb8b5cd20bdcaea9a010ac1f8d835824f5c87a04"
                    ),
                    batch_reward_cap_upper=12 * 10**15,
                    batch_reward_cap_lower=10 * 10**15,
                    quote_reward_cow=6 * 10**18,
                    quote_reward_cap_native=6 * 10**14,
                    service_fee_factor=service_fee_factor,
                    cow_bonding_pool=cow_bonding_pool,
                )
            case _:
                raise ValueError(f"No reward config set up for network {network}.")


@dataclass(frozen=True)
class ProtocolFeeConfig:
    """Configuration for protocol and partner fees.

    Attributes:
    protocol_fee_safe -- address to forward protocol fees to
    partner_fee_cut -- fraction of partner fees withheld from integration partners
    partner_fee_reduced_cut -- reduced amount withheld from partner specified as reduced_cut_address
    reduced_cut_address -- partner fee recipient who pays the reduced cut partner_fee_reduced_cut
    """

    protocol_fee_safe: Address
    partner_fee_cut: float
    partner_fee_reduced_cut: float
    reduced_cut_address: str

    @staticmethod
    def from_network(network: Network) -> ProtocolFeeConfig:
        """Initialize protocol fee config for a given network."""
        match network:
            case Network.MAINNET | Network.GNOSIS | Network.ARBITRUM_ONE:
                return ProtocolFeeConfig(
                    protocol_fee_safe=Address(
                        "0xB64963f95215FDe6510657e719bd832BB8bb941B"
                    ),
                    partner_fee_cut=0.15,
                    partner_fee_reduced_cut=0.10,
                    reduced_cut_address="0x63695Eee2c3141BDE314C5a6f89B98E62808d716",
                )
            case _:
                raise ValueError(
                    f"No protocol fee config set up for network {network}."
                )


@dataclass(frozen=True)
class BufferAccountingConfig:
    """Configuration for buffer accounting."""

    include_slippage: bool

    @staticmethod
    def from_network(network: Network) -> BufferAccountingConfig:
        """Initialize buffer accounting config for a given network."""
        match network:
            case Network.MAINNET:
                include_slippage = True
            case Network.GNOSIS | Network.ARBITRUM_ONE:
                include_slippage = False
            case _:
                raise ValueError(
                    f"No buffer accounting config set up for network {network}."
                )

        return BufferAccountingConfig(
            include_slippage=include_slippage,
        )


@dataclass(frozen=True)
class OrderbookConfig:
    """Configuration for orderbook fetcher"""

    prod_db_url: str
    barn_db_url: str

    @staticmethod
    def from_network(network: Network) -> OrderbookConfig:
        """Initialize orderbook config from environment variables."""
        match network:
            case Network.MAINNET:
                prod_db_url = os.environ.get("PROD_DB_URL_MAINNET", "")
                barn_db_url = os.environ.get("BARN_DB_URL_MAINNET", "")
            case Network.GNOSIS:
                prod_db_url = os.environ.get("PROD_DB_URL_GNOSIS", "")
                barn_db_url = os.environ.get("BARN_DB_URL_GNOSIS", "")
            case Network.ARBITRUM_ONE:
                prod_db_url = os.environ.get("PROD_DB_URL_ARBITRUM", "")
                barn_db_url = os.environ.get("BARN_DB_URL_ARBITRUM", "")
            case _:
                raise ValueError(f"No orderbook config set up for network {network}.")

        return OrderbookConfig(prod_db_url=prod_db_url, barn_db_url=barn_db_url)


@dataclass(frozen=True)
class DuneConfig:
    """Configuration for DuneFetcher."""

    dune_api_key: str
    dune_blockchain: str

    @staticmethod
    def from_network(network: Network) -> DuneConfig:
        """Initialize dune config for a given network."""
        dune_api_key = os.environ.get("DUNE_API_KEY", "")
        match network:
            case Network.MAINNET:
                dune_blockchain = "ethereum"
            case Network.GNOSIS:
                dune_blockchain = "gnosis"
            case Network.ARBITRUM_ONE:
                dune_blockchain = "arbitrum"
            case _:
                raise ValueError(f"No dune config set up for network {network}.")

        return DuneConfig(dune_api_key=dune_api_key, dune_blockchain=dune_blockchain)


@dataclass(frozen=True)
class NodeConfig:
    """Configuration for web3 node."""

    node_url: str

    @staticmethod
    def from_network(network: Network) -> NodeConfig:
        """Initialize node config for a given network."""
        match network:
            case Network.MAINNET:
                node_url = os.environ.get("NODE_URL_MAINNET", "")
            case Network.GNOSIS:
                node_url = os.environ.get("NODE_URL_GNOSIS", "")
            case Network.ARBITRUM_ONE:
                node_url = os.environ.get("NODE_URL_ARBITRUM", "")
            case _:
                raise ValueError(f"No node config set up for network {network}.")

        return NodeConfig(node_url=node_url)


@dataclass(frozen=True)
class PaymentConfig:
    """Configuration of payment."""

    # pylint: disable=too-many-instance-attributes

    network: EthereumNetwork
    cow_token_address: Address
    payment_safe_address: ChecksumAddress
    signing_key: str | None
    safe_queue_url: str
    verification_docs_url: str
    wrapped_native_token_address: ChecksumAddress
    wrapped_eth_address: Address

    @staticmethod
    def from_network(network: Network) -> PaymentConfig:
        """Initialize payment config for a given network."""
        signing_key = os.getenv("PROPOSER_PK")
        if signing_key == "":
            signing_key = None

        docs_url = "https://www.notion.so/cownation/Solver-Payouts-3dfee64eb3d449ed8157a652cc817a8c"

        match network:
            case Network.MAINNET:
                payment_network = EthereumNetwork.MAINNET
                payment_safe_address = Web3.to_checksum_address(
                    os.environ.get(
                        "PAYOUTS_SAFE_ADDRESS_MAINNET",
                        "0xA03be496e67Ec29bC62F01a428683D7F9c204930",
                    )
                )
                short_name = "eth"

                cow_token_address = Address(
                    "0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB"
                )
                wrapped_native_token_address = Web3.to_checksum_address(
                    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
                )
                wrapped_eth_address = Address(
                    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
                )

            case Network.GNOSIS:
                payment_network = EthereumNetwork.GNOSIS
                payment_safe_address = Web3.to_checksum_address(
                    os.environ.get("PAYOUTS_SAFE_ADDRESS_GNOSIS", "")
                )
                short_name = "gno"

                cow_token_address = Address(
                    "0x177127622c4a00f3d409b75571e12cb3c8973d3c"
                )
                wrapped_native_token_address = Web3.to_checksum_address(
                    "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d"
                )
                wrapped_eth_address = Address(
                    "0x6a023ccd1ff6f2045c3309768ead9e68f978f6e1"
                )
            case Network.ARBITRUM_ONE:
                payment_network = EthereumNetwork.GNOSIS
                payment_safe_address = Web3.to_checksum_address(
                    os.environ.get("PAYOUTS_SAFE_ADDRESS_ARBITRUM", "")
                )
                short_name = "arb1"

                cow_token_address = Address(
                    "0xcb8b5cd20bdcaea9a010ac1f8d835824f5c87a04"
                )
                wrapped_native_token_address = Web3.to_checksum_address(
                    "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"
                )
                wrapped_eth_address = Address(
                    "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"
                )
            case _:
                raise ValueError(f"No payment config set up for network {network}.")

        safe_url = f"https://app.safe.global/{short_name}:{payment_safe_address}"
        safe_queue_url = f"{safe_url}/transactions/queue"

        return PaymentConfig(
            network=payment_network,
            cow_token_address=cow_token_address,
            payment_safe_address=payment_safe_address,
            signing_key=signing_key,
            safe_queue_url=safe_queue_url,
            verification_docs_url=docs_url,
            wrapped_native_token_address=wrapped_native_token_address,
            wrapped_eth_address=wrapped_eth_address,
        )


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

    @staticmethod
    def from_env() -> IOConfig:
        """Initialize io config from environment variables."""
        slack_channel = os.getenv("SLACK_CHANNEL", None)
        slack_token = os.getenv("SLACK_TOKEN", None)

        project_root_dir = Path(__file__).parent.parent
        file_out_dir = project_root_dir / Path("out")
        log_config_file = project_root_dir / Path("logging.conf")
        query_dir = project_root_dir / Path("queries")
        dashboard_dir = project_root_dir / Path("dashboards/solver-rewards-accounting")

        return IOConfig(
            project_root_dir=project_root_dir,
            log_config_file=log_config_file,
            query_dir=query_dir,
            csv_output_dir=file_out_dir,
            dashboard_dir=dashboard_dir,
            slack_channel=slack_channel,
            slack_token=slack_token,
        )


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

    @staticmethod
    def from_network(network: Network) -> AccountingConfig:
        """Initialize accounting config for a given network."""

        return AccountingConfig(
            payment_config=PaymentConfig.from_network(network),
            orderbook_config=OrderbookConfig.from_network(network),
            dune_config=DuneConfig.from_network(network),
            node_config=NodeConfig.from_network(network),
            reward_config=RewardConfig.from_network(network),
            protocol_fee_config=ProtocolFeeConfig.from_network(network),
            buffer_accounting_config=BufferAccountingConfig.from_network(network),
            io_config=IOConfig.from_env(),
        )


web3 = Web3(
    Web3.HTTPProvider(
        NodeConfig.from_network(Network(os.environ.get("NETWORK", "mainnet"))).node_url
    )
)
