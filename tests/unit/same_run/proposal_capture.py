"""Runs CoW's real ``auto_propose`` offline and captures what it would post.

``propose`` calls ``auto_propose`` from ``src/fetch/transfer_file.py``,
unmodified, for one ``PayoutScenario``. The configuration is built from the
run's environment variables by ``AccountingConfig.from_network``, as ``main()``
builds it. Only the network edges are replaced:

- ``EthereumClient`` construction: safe-eth-py's own client, whose HTTP
  session sends the requests for each node URL to that chain's ``FakeNode``;
- ``TransactionServiceApi.post_transaction``: the signed Safe transaction is
  captured instead of posted;
- ``post_to_slack``: the channel is recorded instead of posted to;
- ``time.sleep`` in ``src.multisend``: the pause is recorded, not waited.

Everything else runs as in a real payout run: the payout lists, the balance
check and unwrap, the nonces, the MultiSend encoding, hashing and signing.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import create_autospec, patch

from eth_typing import URI
from requests import Session
from safe_eth.eth import ethereum_client
from safe_eth.eth.ethereum_client import EthereumClient
from safe_eth.safe.api import TransactionServiceApi
from safe_eth.safe.safe_tx import SafeTx
from safe_eth.util.http import prepare_http_session
from slack.web.client import WebClient

from src import multisend
from src.config import AccountingConfig, Network
from src.fetch import transfer_file
from src.utils.print_store import PrintStore
from src.verification.safe_transaction import SafeTransaction
from tests.unit.same_run.fake_node import FakeNode, RpcRequest
from tests.unit.same_run.scenarios import (
    ARBITRUM_NODE_URL,
    MAINNET_NODE_URL,
    PayoutScenario,
)


@dataclass(frozen=True)
class ProposedTransaction:
    """A Safe transaction as ``auto_propose`` would have posted it: the signed
    fields, the safeTxHash safe-eth-py computed for it and the base URL of the
    Transaction Service instance it was for."""

    transaction: SafeTransaction
    safe_tx_hash: bytes
    service_url: str


@dataclass(frozen=True)
class ProposalRun:
    """Everything one ``auto_propose`` run sent to the outside world."""

    proposals: tuple[ProposedTransaction, ...]
    mainnet_requests: tuple[RpcRequest, ...]
    arbitrum_requests: tuple[RpcRequest, ...]
    sleeps: tuple[float, ...]
    slack_channels: tuple[str, ...]
    slack_client_calls: int


def propose(scenario: PayoutScenario) -> ProposalRun:
    """Run ``auto_propose`` for ``scenario``, posting nothing.

    The proposals are in posting order.
    """
    mainnet = FakeNode(MAINNET_NODE_URL, scenario.mainnet_chain())
    arbitrum = FakeNode(ARBITRUM_NODE_URL, scenario.arbitrum_chain())
    proposals: list[ProposedTransaction] = []
    sleeps: list[float] = []
    slack_channels: list[str] = []

    def post_transaction(service: TransactionServiceApi, safe_tx: SafeTx) -> bool:
        proposals.append(_proposed(service, safe_tx))
        return True

    def post_to_slack(*_: object, channel: str, **__: object) -> None:
        slack_channels.append(channel)

    slack_client = create_autospec(WebClient, instance=True)
    with patch.dict(os.environ, scenario.environment(), clear=True):
        config = AccountingConfig.from_network(Network(os.environ["NETWORK"]))
        with (
            patch.object(transfer_file, "EthereumClient", _connect(mainnet, arbitrum)),
            patch.object(TransactionServiceApi, "post_transaction", post_transaction),
            patch.object(transfer_file, "post_to_slack", post_to_slack),
            patch.object(multisend, "time", SimpleNamespace(sleep=sleeps.append)),
        ):
            transfer_file.auto_propose(
                transfers_cow=list(scenario.transfers_cow),
                transfers_native=list(scenario.transfers_native),
                overdrafts=list(scenario.overdrafts),
                log_saver_obj=PrintStore(),
                slack_client=slack_client,
                dry_run=False,
                config=config,
            )
    return ProposalRun(
        proposals=tuple(proposals),
        mainnet_requests=mainnet.requests,
        arbitrum_requests=arbitrum.requests,
        sleeps=tuple(sleeps),
        slack_channels=tuple(slack_channels),
        slack_client_calls=len(slack_client.mock_calls),
    )


def _connect(*nodes: FakeNode) -> Callable[[URI], EthereumClient]:
    """``EthereumClient`` construction, connected to the fake nodes.

    The constructor makes its HTTP session with ``prepare_http_session`` and
    reads the chain id straight away, so the node for the client's URL is
    mounted on the session as the session is made.
    """
    nodes_by_url = {node.url: node for node in nodes}

    def connect(url: URI) -> EthereumClient:
        node = nodes_by_url[url]

        def session_with_node(*args: Any, **kwargs: Any) -> Session:
            session = prepare_http_session(*args, **kwargs)
            node.mount(session)
            return session

        with patch.object(ethereum_client, "prepare_http_session", session_with_node):
            return EthereumClient(url)

    return connect


def _proposed(service: TransactionServiceApi, safe_tx: SafeTx) -> ProposedTransaction:
    return ProposedTransaction(
        transaction=SafeTransaction(
            chain_id=safe_tx.chain_id,
            safe=safe_tx.safe_address,
            to=safe_tx.to,
            value=safe_tx.value,
            data=bytes(safe_tx.data),
            operation=safe_tx.operation,
            safe_tx_gas=safe_tx.safe_tx_gas,
            base_gas=safe_tx.base_gas,
            gas_price=safe_tx.gas_price,
            gas_token=safe_tx.gas_token,
            refund_receiver=safe_tx.refund_receiver,
            nonce=safe_tx.safe_nonce,
        ),
        safe_tx_hash=bytes(safe_tx.safe_tx_hash),
        service_url=service.base_url,
    )
