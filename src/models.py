"""
Common location for shared resources throughout the project.
"""
from enum import Enum


class Network(Enum):
    """
    Enum for EVM network. Meant to be used everywhere instead of strings
    """
    MAINNET = 'mainnet'
    GCHAIN = 'gchain'
