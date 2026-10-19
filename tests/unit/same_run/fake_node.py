"""An in-process Ethereum node that answers the chain reads of a payout run.

``auto_propose`` reads the chain through safe-eth-py's ``EthereumClient``,
whose web3 provider posts JSON-RPC requests with ``requests``. A ``FakeNode``
is mounted on the client's ``requests`` session as the transport adapter for
the node URL, so web3's encoding, middleware and request cache run unchanged
and no connection is ever opened.

The node answers exactly these reads, at the ``latest`` block:

- ``eth_chainId``;
- ``eth_getBalance`` of an address it has a native balance for;
- ``eth_getCode`` of an address it has code for;
- ``eth_call`` of a Safe's ``nonce()`` or ``VERSION()``, and of an ERC-20
  ``balanceOf(holder)`` it has a balance for.

Every request is recorded, in order. Any other request raises
``UnexpectedRequest``, an ``AssertionError``: library code around these reads
catches ``Web3Exception``, ``ValueError`` and ``OSError`` (``Safe`` falls back
to a default version when reading ``VERSION()`` fails), and an unexpected read
must fail the test rather than be absorbed.
"""

from __future__ import annotations

import io
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from eth_abi.abi import encode
from eth_utils.abi import function_signature_to_4byte_selector
from eth_utils.address import to_checksum_address
from requests import PreparedRequest, Response, Session
from requests.adapters import BaseAdapter

_NONCE = function_signature_to_4byte_selector("nonce()")
_VERSION = function_signature_to_4byte_selector("VERSION()")
_BALANCE_OF = function_signature_to_4byte_selector("balanceOf(address)")
_REQUEST_MEMBERS = frozenset({"jsonrpc", "id", "method", "params"})


class UnexpectedRequest(AssertionError):
    """The node received a request it has no answer for."""


@dataclass(frozen=True)
class RpcRequest:
    """One JSON-RPC request, with its parameters as decoded from JSON."""

    method: str
    params: Any


@dataclass(frozen=True)
class SafeState:
    """What a Safe returns to ``nonce()`` and ``VERSION()``."""

    nonce: int
    version: str


@dataclass(frozen=True)
class ChainState:
    """What a node knows about its chain: native balances, deployed code,
    Safes, and ERC-20 balances by (token, holder). Addresses may be in any
    case."""

    chain_id: int
    balances: Mapping[str, int] = field(default_factory=dict)
    code: Mapping[str, bytes] = field(default_factory=dict)
    safes: Mapping[str, SafeState] = field(default_factory=dict)
    token_balances: Mapping[tuple[str, str], int] = field(default_factory=dict)


class FakeNode:
    """The node of one chain, reachable at ``url`` once mounted on a session."""

    def __init__(self, url: str, chain: ChainState) -> None:
        self.url = url
        self._answers = _answers(chain)
        self._requests: list[RpcRequest] = []

    @property
    def requests(self) -> tuple[RpcRequest, ...]:
        """Every request the node received, in order, answered or not."""
        return tuple(self._requests)

    def mount(self, session: Session) -> None:
        """Send ``session``'s requests for this node's URL to this node."""
        session.mount(self.url, _Transport(self))

    def reply(self, body: object) -> dict[str, Any]:
        """The JSON-RPC response to one decoded request body."""
        if not isinstance(body, dict) or set(body) != _REQUEST_MEMBERS:
            raise UnexpectedRequest(f"{self.url}: not a JSON-RPC request: {body!r}")
        request = RpcRequest(method=body["method"], params=body["params"])
        self._requests.append(request)
        key = _request_key(request)
        if key is None or key not in self._answers:
            raise UnexpectedRequest(f"{self.url}: no answer for {request}")
        return {"jsonrpc": "2.0", "id": body["id"], "result": self._answers[key]}


class _Transport(BaseAdapter):
    """A ``requests`` transport adapter that hands requests to a fake node."""

    def __init__(self, node: FakeNode) -> None:
        super().__init__()
        self._node = node

    def send(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: None | bytes | str | tuple[bytes | str, bytes | str] = None,
        proxies: Mapping[str, str] | None = None,
    ) -> Response:
        """Answer ``request`` in process.

        The connection settings are ignored: nothing is sent anywhere.
        """
        del stream, timeout, verify, cert, proxies
        if request.body is None:
            raise UnexpectedRequest(f"{self._node.url}: request without a body")
        reply = self._node.reply(json.loads(request.body))
        response = Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response.raw = io.BytesIO(json.dumps(reply).encode())
        response.url = request.url or self._node.url
        response.request = request
        return response

    def close(self) -> None:
        """Nothing to release: no connection is ever opened."""


def _answers(chain: ChainState) -> dict[tuple[object, ...], str]:
    answers: dict[tuple[object, ...], str] = {("eth_chainId",): hex(chain.chain_id)}
    for address, balance in chain.balances.items():
        answers["eth_getBalance", to_checksum_address(address)] = hex(balance)
    for address, code in chain.code.items():
        answers["eth_getCode", to_checksum_address(address)] = _hex(code)
    for address, safe in chain.safes.items():
        safe_address = to_checksum_address(address)
        answers["eth_call", safe_address, _NONCE] = _hex(
            encode(["uint256"], [safe.nonce])
        )
        answers["eth_call", safe_address, _VERSION] = _hex(
            encode(["string"], [safe.version])
        )
    for (token, holder), balance in chain.token_balances.items():
        call = _BALANCE_OF + encode(["address"], [to_checksum_address(holder)])
        answers["eth_call", to_checksum_address(token), call] = _hex(
            encode(["uint256"], [balance])
        )
    return answers


def _request_key(request: RpcRequest) -> tuple[object, ...] | None:
    """The answer a request asks for, or None if the node serves no such read.

    Addresses and calldata are compared as values, as a node does, not as
    spelled; the request log keeps the spelling.
    """
    try:
        match request.method, request.params:
            case "eth_chainId", []:
                return ("eth_chainId",)
            case ("eth_getBalance" | "eth_getCode") as method, [
                str() as address,
                "latest",
            ]:
                return (method, to_checksum_address(address))
            case "eth_call", [
                {"to": str() as to, "data": str() as data, **other},
                "latest",
            ] if not other and data.startswith("0x"):
                return ("eth_call", to_checksum_address(to), bytes.fromhex(data[2:]))
    except ValueError:
        return None
    return None


def _hex(data: bytes) -> str:
    return "0x" + data.hex()
