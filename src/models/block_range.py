"""
BlockRange Model is just a data class for left and right bounds
"""

from dataclasses import dataclass


@dataclass
class BlockRange:
    """
    Basic dataclass for an Ethereum block range with some Dune compatibility methods.
    TODO (easy) - this data class could probably live in dune-client.
    https://github.com/cowprotocol/dune-bridge/issues/40
    """

    block_from: int
    block_to: int

    def __str__(self) -> str:
        return f"BlockRange(from={self.block_from}, to={self.block_to})"

    def __repr__(self) -> str:
        return str(self)
