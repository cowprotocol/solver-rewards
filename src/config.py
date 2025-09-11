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
from safe_eth.eth.ethereum_network import EthereumNetwork
from web3 import Web3

load_dotenv()


class Network(Enum):
    """Network class for networks supported by the accounting."""

    MAINNET = "mainnet"
    BASE = "base"
    ARBITRUM_ONE = "arbitrum"
    LENS = "lens"
    GNOSIS = "gnosis"
    AVALANCHE = "avalanche"
    POLYGON = "polygon"


@dataclass(frozen=True)
class RewardConfig:
    """Configuration for reward mechanism."""

    reward_token_address: Address
    batch_reward_cap_upper: int
    batch_reward_cap_lower: int
    quote_reward_cow: int
    quote_reward_cap_native: int
    service_fee_factor: Fraction

    @staticmethod
    def from_network(network: Network) -> RewardConfig:
        """Initialize reward config for a given network."""
        service_fee_factor = Fraction(15, 100)
        reward_token_address = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
        match network:
            case Network.MAINNET:
                batch_reward_cap_upper = 12 * 10**15
                batch_reward_cap_lower = 10 * 10**15
                quote_reward_cow = 6 * 10**18
                quote_reward_cap_native = 7 * 10**14
            case Network.GNOSIS:
                batch_reward_cap_upper = 10 * 10**18
                batch_reward_cap_lower = 10 * 10**18
                quote_reward_cow = 6 * 10**18
                quote_reward_cap_native = 15 * 10**16
            case Network.ARBITRUM_ONE:
                batch_reward_cap_upper = 12 * 10**15
                batch_reward_cap_lower = 10 * 10**15
                quote_reward_cow = 6 * 10**18
                quote_reward_cap_native = 24 * 10**13
            case Network.BASE:
                batch_reward_cap_upper = 12 * 10**15
                batch_reward_cap_lower = 10 * 10**15
                quote_reward_cow = 6 * 10**18
                quote_reward_cap_native = 24 * 10**13
            case Network.AVALANCHE:
                batch_reward_cap_upper = 4 * 10**17
                batch_reward_cap_lower = 3 * 10**17
                quote_reward_cow = 6 * 10**18
                quote_reward_cap_native = 6 * 10**15
            case Network.POLYGON:
                batch_reward_cap_upper = 40 * 10**18
                batch_reward_cap_lower = 30 * 10**18
                quote_reward_cow = 6 * 10**18
                quote_reward_cap_native = 6 * 10**17
            case Network.LENS:
                batch_reward_cap_upper = 10 * 10**18
                batch_reward_cap_lower = 10 * 10**18
                quote_reward_cow = 6 * 10**18
                quote_reward_cap_native = 15 * 10**16
            case _:
                raise ValueError(f"No reward config set up for network {network}.")
        return RewardConfig(
            reward_token_address=reward_token_address,
            batch_reward_cap_upper=batch_reward_cap_upper,
            batch_reward_cap_lower=batch_reward_cap_lower,
            quote_reward_cow=quote_reward_cow,
            quote_reward_cap_native=quote_reward_cap_native,
            service_fee_factor=service_fee_factor,
        )


@dataclass(frozen=True)
class ProtocolFeeConfig:
    """Configuration for protocol and partner fees.

    Attributes:
    protocol_fee_safe -- address to forward protocol fees to
    default_partner_fee_cut -- default fraction of partner fees withheld from integration partners
    custom_partner_fee_dict -- dictionary of partner_fee_recipients/app_code pairs and
        corresponding fractions. here, we use the convention that if there is an explicit
        recipient+app_code match, the corresponding fraction applies, while if there is no
        such match but there is still a recipient match with the custom (recipient, "") entry
        in the dictionary, that entry is matched. In other words, the empty string "" serves
        as placeholder here.
    """

    protocol_fee_safe: Address
    default_partner_fee_cut: float
    custom_partner_fee_dict: dict[tuple[str, str], float]

    @staticmethod
    def from_network(network: Network) -> ProtocolFeeConfig:
        """Initialize protocol fee config for a given network."""
        protocol_fee_safe = Address("0x22af3D38E50ddedeb7C47f36faB321eC3Bb72A76")
        match network:
            case Network.MAINNET:
                custom_partner_fee_dict = {
                    (
                        "0x63695eee2c3141bde314c5a6f89b98e62808d716",
                        "CoW Swap-SafeApp",
                    ): 0.50,
                    ("0x63695eee2c3141bde314c5a6f89b98e62808d716", ""): 0.10,
                    (
                        "0x8025bacf968aa82bdfe51b513123b55bfb0060d3",
                        "CoW Swap-SafeApp",
                    ): 0.55,
                    ("0xe344241493d573428076c022835856a221db3e26", ""): 0.15,
                    ("0x352a3666b27bb09aca7b4a71ed624429b7549551", ""): 0.15,
                    ("0xe37da2d07e769b7fcb808bdeaeffb84561ff4eca", ""): 0.15,
                    ("0x90a48d5cf7343b08da12e067680b4c6dbfe551be", ""): 0.15,
                    ("0xcd777a10502256db93c2b0a8e8f64a5174c6cbda", ""): 0.15,
                    ("0xe423c63e8a25811c9cbe71c8585c4505117397c6", ""): 0.25,
                    ("0x1713b79e3dbb8a76d80e038ca701a4a781ac69eb", ""): 0.25,
                    ("0xc542c2f197c4939154017c802b0583c596438380", ""): 0.125,
                }
            case Network.GNOSIS:
                custom_partner_fee_dict = {
                    (
                        "0x63695eee2c3141bde314c5a6f89b98e62808d716",
                        "CoW Swap-SafeApp",
                    ): 0.50,
                    ("0x63695eee2c3141bde314c5a6f89b98e62808d716", ""): 0.10,
                    (
                        "0x8025bacf968aa82bdfe51b513123b55bfb0060d3",
                        "CoW Swap-SafeApp",
                    ): 0.55,
                    ("0xe344241493d573428076c022835856a221db3e26", ""): 0.15,
                    ("0x352a3666b27bb09aca7b4a71ed624429b7549551", ""): 0.15,
                    ("0x8387fae9951724c00c753797b22b897111750673", ""): 0.15,
                    ("0xb0E3175341794D1dc8E5F02a02F9D26989EbedB3", ""): 0.15,
                    ("0xcd777a10502256db93c2b0a8e8f64a5174c6cbda", ""): 0.15,
                    ("0xe423c63e8a25811c9cbe71c8585c4505117397c6", ""): 0.25,
                    ("0x1713b79e3dbb8a76d80e038ca701a4a781ac69eb", ""): 0.25,
                    ("0xc542c2f197c4939154017c802b0583c596438380", ""): 0.125,
                }
            case Network.ARBITRUM_ONE:
                custom_partner_fee_dict = {
                    (
                        "0x63695eee2c3141bde314c5a6f89b98e62808d716",
                        "CoW Swap-SafeApp",
                    ): 0.50,
                    ("0x63695eee2c3141bde314c5a6f89b98e62808d716", ""): 0.10,
                    (
                        "0x8025bacf968aa82bdfe51b513123b55bfb0060d3",
                        "CoW Swap-SafeApp",
                    ): 0.55,
                    ("0xe344241493d573428076c022835856a221db3e26", ""): 0.15,
                    ("0x352a3666b27bb09aca7b4a71ed624429b7549551", ""): 0.15,
                    ("0x86cd2bBC859E797B75D86E6eEEC1a726A9284c23", ""): 0.15,
                    ("0x38276553F8fbf2A027D901F8be45f00373d8Dd48", ""): 0.15,
                    ("0xcd777a10502256db93c2b0a8e8f64a5174c6cbda", ""): 0.15,
                    ("0xe423c63e8a25811c9cbe71c8585c4505117397c6", ""): 0.25,
                    ("0x1713b79e3dbb8a76d80e038ca701a4a781ac69eb", ""): 0.25,
                    ("0xc542c2f197c4939154017c802b0583c596438380", ""): 0.125,
                }
            case Network.BASE:
                custom_partner_fee_dict = {
                    (
                        "0x63695eee2c3141bde314c5a6f89b98e62808d716",
                        "CoW Swap-SafeApp",
                    ): 0.50,
                    ("0x63695eee2c3141bde314c5a6f89b98e62808d716", ""): 0.10,
                    (
                        "0x8025bacf968aa82bdfe51b513123b55bfb0060d3",
                        "CoW Swap-SafeApp",
                    ): 0.55,
                    ("0xe344241493d573428076c022835856a221db3e26", ""): 0.15,
                    ("0x352a3666b27bb09aca7b4a71ed624429b7549551", ""): 0.15,
                    ("0xAf1c727B605530AcDb00906a158E817f41aFD778", ""): 0.15,
                    ("0x9c9aA90363630d4ab1D9dbF416cc3BBC8d3Ed502", ""): 0.15,
                    ("0xcd777a10502256db93c2b0a8e8f64a5174c6cbda", ""): 0.15,
                    ("0xe423c63e8a25811c9cbe71c8585c4505117397c6", ""): 0.25,
                    ("0x1713b79e3dbb8a76d80e038ca701a4a781ac69eb", ""): 0.25,
                    ("0xc542c2f197c4939154017c802b0583c596438380", ""): 0.125,
                }
            case Network.AVALANCHE:
                # dummy values, will not be used
                custom_partner_fee_dict = {}
            case Network.POLYGON:
                # dummy values, will not be used
                custom_partner_fee_dict = {}
            case Network.LENS:
                # dummy values, will not be used
                custom_partner_fee_dict = {}
            case _:
                raise ValueError(
                    f"No protocol fee config set up for network {network}."
                )
        return ProtocolFeeConfig(
            protocol_fee_safe=protocol_fee_safe,
            default_partner_fee_cut=0.5,
            custom_partner_fee_dict=custom_partner_fee_dict,
        )


@dataclass(frozen=True)
class BufferAccountingConfig:
    """Configuration for buffer accounting."""

    include_slippage: bool
    send_buffers_to_rewards_address_pools: list[Address]

    @staticmethod
    def from_network(network: Network) -> BufferAccountingConfig:
        """Initialize buffer accounting config for a given network."""
        send_buffers_to_rewards_address_pools = [
            Address(
                "0x5d4020b9261f01b6f8a45db929704b0ad6f5e9e6"
            ),  # CoW DAO bonding pool
            Address(
                "0x0deb0ae9c4399c51289adb1f3ed83557a56df657"
            ),  # Rizzolver bonding pool
            Address(
                "0x7719c9c0d35d460b00487a1744394e9525e8a42c"
            ),  # Fractal bonding pool
        ]
        match network:
            case (
                Network.MAINNET
                | Network.GNOSIS
                | Network.ARBITRUM_ONE
                | Network.BASE
                | Network.AVALANCHE
                | Network.POLYGON
                | Network.LENS
            ):
                include_slippage = True
            case _:
                raise ValueError(
                    f"No buffer accounting config set up for network {network}."
                )

        return BufferAccountingConfig(
            include_slippage=include_slippage,
            send_buffers_to_rewards_address_pools=send_buffers_to_rewards_address_pools,
        )


@dataclass(frozen=True)
class OrderbookConfig:
    """Configuration for orderbook fetcher"""

    prod_db_url: str
    barn_db_url: str
    analytics_db_url: str
    network_db_name: str
    schema: str

    @staticmethod
    def from_network(network: Network) -> OrderbookConfig:
        """Initialize orderbook config from environment variables."""
        prod_db_url = os.environ.get("PROD_DB_URL", "")
        barn_db_url = os.environ.get("BARN_DB_URL", "")
        analytics_db_url = os.environ.get("ANALYTICS_DB_URL", "")
        schema = "dbt"
        match network:
            case Network.MAINNET:
                network_db_name = "mainnet"
            case Network.GNOSIS:
                network_db_name = "xdai"
            case Network.ARBITRUM_ONE:
                network_db_name = "arbitrum-one"
            case Network.BASE:
                network_db_name = "base"
            case Network.AVALANCHE:
                network_db_name = "avalanche"
            case Network.POLYGON:
                network_db_name = "polygon"
            case Network.LENS:
                network_db_name = "lens"
            case _:
                raise ValueError(
                    f"No orderbook data base config set up for network {network}."
                )

        return OrderbookConfig(
            prod_db_url=prod_db_url,
            barn_db_url=barn_db_url,
            analytics_db_url=analytics_db_url,
            network_db_name=network_db_name,
            schema=schema,
        )


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
            case Network.BASE:
                dune_blockchain = "base"
            case Network.AVALANCHE:
                dune_blockchain = "avalanche_c"
            case Network.POLYGON:
                dune_blockchain = "polygon"
            case Network.LENS:
                dune_blockchain = "lens"
            case _:
                raise ValueError(f"No dune config set up for network {network}.")

        return DuneConfig(dune_api_key=dune_api_key, dune_blockchain=dune_blockchain)


@dataclass(frozen=True)
class NodeConfig:
    """Configuration for web3 node."""

    node_url: str
    node_url_mainnet: str

    @staticmethod
    def from_env() -> NodeConfig:
        """Initialize node config from environment variables."""
        node_url = os.environ.get("NODE_URL", "")
        node_url_mainnet = os.environ.get("NODE_URL_MAINNET", "")
        return NodeConfig(node_url=node_url, node_url_mainnet=node_url_mainnet)


@dataclass(frozen=True)
class PaymentConfig:
    """Configuration of payment."""

    # pylint: disable=too-many-instance-attributes

    network: EthereumNetwork
    cow_token_address: Address
    payment_safe_address_cow: ChecksumAddress
    payment_safe_address_native: ChecksumAddress
    signing_key: str | None
    nonce_modifier: int
    safe_queue_url_cow: str
    safe_queue_url_native: str
    verification_docs_url: str
    wrapped_native_token_address: ChecksumAddress
    wrapped_eth_address: Address
    min_native_token_transfer: int
    min_cow_transfer: int

    @staticmethod
    def from_network(network: Network) -> PaymentConfig:
        """Initialize payment config for a given network."""
        # pylint: disable=too-many-locals,too-many-statements
        signing_key = os.getenv("PROPOSER_PK")
        if signing_key == "":
            signing_key = None

        docs_url = "https://www.notion.so/cownation/Solver-Payouts-3dfee64eb3d449ed8157a652cc817a8c"

        cow_token_address = Address("0xDEf1CA1fb7FBcDC777520aa7f396b4E015F497aB")
        payment_safe_address_cow = Web3.to_checksum_address(
            os.environ.get(
                "PAYOUTS_SAFE_ADDRESS_MAINNET",
                "",
            )
        )
        payment_safe_address_native = Web3.to_checksum_address(
            os.environ.get(
                "PAYOUTS_SAFE_ADDRESS",
                "",
            )
        )

        # mainnet transaction nonces are increased by this modifier to allow for proposing
        # multiple transactions on mainnet
        nonce_modifier_dict = {
            network: idx for idx, network in enumerate(reversed(list(Network)), start=0)
        }
        nonce_modifier = int(
            os.environ.get(
                "NONCE_MODIFIER",
                nonce_modifier_dict[network],
            )
        )

        match network:
            case Network.MAINNET:
                payment_network = EthereumNetwork.MAINNET
                short_name = "eth"

                wrapped_native_token_address = Web3.to_checksum_address(
                    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
                )
                wrapped_eth_address = Address(
                    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
                )
                min_native_token_transfer = 10**15  # 0.001 ETH
                min_cow_transfer = 10 * 10**18  # 10 COW

            case Network.GNOSIS:
                payment_network = EthereumNetwork.GNOSIS
                short_name = "gno"

                wrapped_native_token_address = Web3.to_checksum_address(
                    "0xe91d153e0b41518a2ce8dd3d7944fa863463a97d"
                )
                wrapped_eth_address = Address(
                    "0x6a023ccd1ff6f2045c3309768ead9e68f978f6e1"
                )
                min_native_token_transfer = 10**16  # 0.01 xDAI
                min_cow_transfer = 10**18  # 1 COW

            case Network.ARBITRUM_ONE:
                payment_network = EthereumNetwork.ARBITRUM_ONE
                short_name = "arb1"

                wrapped_native_token_address = Web3.to_checksum_address(
                    "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"
                )
                wrapped_eth_address = Address(
                    "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"
                )
                min_native_token_transfer = 10**14  # 0.0001 ETH
                min_cow_transfer = 10**18  # 1 COW

            case Network.BASE:
                payment_network = EthereumNetwork.BASE
                short_name = "base"

                wrapped_native_token_address = Web3.to_checksum_address(
                    "0x4200000000000000000000000000000000000006"
                )
                wrapped_eth_address = Address(
                    "0x4200000000000000000000000000000000000006"
                )
                min_native_token_transfer = 10**14  # 0.0001 ETH
                min_cow_transfer = 10**18  # 1 COW

            case Network.AVALANCHE:
                payment_network = EthereumNetwork.AVALANCHE_C_CHAIN
                short_name = "avax"

                cow_token_address = Address(  # dummy address
                    "0x0000000000000000000000000000000000000006"
                )
                wrapped_native_token_address = Web3.to_checksum_address(  # wrapped AVAX
                    "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"
                )
                wrapped_eth_address = Address(  # real address
                    "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB"
                )
                min_native_token_transfer = 10**14  # 0.0001 AVAX
                min_cow_transfer = 10**18  # 1 COW

            case Network.POLYGON:
                payment_network = EthereumNetwork.POLYGON
                short_name = "matic"

                cow_token_address = Address(  # dummy address
                    "0x0000000000000000000000000000000000000006"
                )
                wrapped_native_token_address = Web3.to_checksum_address(  # wrapped POL
                    "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"
                )
                wrapped_eth_address = Address(  # real address
                    "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"
                )
                min_native_token_transfer = 10**14  # 0.0001 POL
                min_cow_transfer = 10**18  # 1 COW

            case Network.LENS:
                payment_network = EthereumNetwork.LENS
                short_name = "gho"

                wrapped_native_token_address = Web3.to_checksum_address(
                    "0x6bDc36E20D267Ff0dd6097799f82e78907105e2F"
                )
                wrapped_eth_address = Address(
                    "0xe5ecd226b3032910ceaa43ba92ee8232f8237553"
                )
                min_native_token_transfer = 10**16  # 0.01 GHO
                min_cow_transfer = 10**18  # 1 COW
            case _:
                raise ValueError(f"No payment config set up for network {network}.")

        safe_url_cow = f"https://app.safe.global/eth:{payment_safe_address_cow}"
        safe_queue_url_cow = f"{safe_url_cow}/transactions/queue"
        safe_url_native = (
            f"https://app.safe.global/{short_name}:{payment_safe_address_native}"
        )
        safe_queue_url_native = f"{safe_url_native}/transactions/queue"

        return PaymentConfig(
            network=payment_network,
            cow_token_address=cow_token_address,
            payment_safe_address_cow=payment_safe_address_cow,
            payment_safe_address_native=payment_safe_address_native,
            signing_key=signing_key,
            nonce_modifier=nonce_modifier,
            safe_queue_url_cow=safe_queue_url_cow,
            safe_queue_url_native=safe_queue_url_native,
            verification_docs_url=docs_url,
            wrapped_native_token_address=wrapped_native_token_address,
            wrapped_eth_address=wrapped_eth_address,
            min_native_token_transfer=min_native_token_transfer,
            min_cow_transfer=min_cow_transfer,
        )


@dataclass(frozen=True)
class IOConfig:
    """Configuration of input and output."""

    # pylint: disable=too-many-instance-attributes

    network: Network
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
        network = Network(os.getenv("NETWORK"))
        slack_channel = os.getenv("SLACK_CHANNEL", None)
        slack_token = os.getenv("SLACK_TOKEN", None)

        project_root_dir = Path(__file__).parent.parent
        file_out_dir = project_root_dir / Path("out")
        log_config_file = project_root_dir / Path("logging.conf")
        query_dir = project_root_dir / Path("queries")
        dashboard_dir = project_root_dir / Path("dashboards/solver-rewards-accounting")

        return IOConfig(
            network=network,
            project_root_dir=project_root_dir,
            log_config_file=log_config_file,
            query_dir=query_dir,
            csv_output_dir=file_out_dir,
            dashboard_dir=dashboard_dir,
            slack_channel=slack_channel,
            slack_token=slack_token,
        )


@dataclass(frozen=True)
class DataProcessingConfig:
    """Configuration of data processing component."""

    # pylint: disable=too-many-instance-attributes
    bucket_size: int

    @staticmethod
    def from_network(network: Network) -> DataProcessingConfig:
        """Initialize data processing config for a given network."""
        match network:
            case Network.MAINNET:
                bucket_size = 10000
            case Network.GNOSIS:
                bucket_size = 30000
            case Network.ARBITRUM_ONE:
                bucket_size = 1000000
            case Network.BASE:
                bucket_size = 50000
            case Network.AVALANCHE:
                bucket_size = 0  # dummy value
            case Network.POLYGON:
                bucket_size = 0  # dummy value
            case Network.LENS:
                bucket_size = 0  # dummy value
            case _:
                raise ValueError(
                    f"No buffer accounting config set up for network {network}."
                )

        return DataProcessingConfig(
            bucket_size=bucket_size,
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
    data_processing_config: DataProcessingConfig

    @staticmethod
    def from_network(network: Network) -> AccountingConfig:
        """Initialize accounting config for a given network."""

        return AccountingConfig(
            payment_config=PaymentConfig.from_network(network),
            orderbook_config=OrderbookConfig.from_network(network),
            dune_config=DuneConfig.from_network(network),
            node_config=NodeConfig.from_env(),
            reward_config=RewardConfig.from_network(network),
            protocol_fee_config=ProtocolFeeConfig.from_network(network),
            buffer_accounting_config=BufferAccountingConfig.from_network(network),
            io_config=IOConfig.from_env(),
            data_processing_config=DataProcessingConfig.from_network(network),
        )


web3 = Web3(Web3.HTTPProvider(NodeConfig.from_env().node_url))
