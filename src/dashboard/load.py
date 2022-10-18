"""
Script to fetch/load dashboard into a config file.
Essentially scraping SQL from Dune
"""
from duneapi.dashboard import DuneDashboard

from src.dashboard.common import arg_parse

if __name__ == "__main__":
    dune_connection, args = arg_parse(description="Load Dashboard")
    dashboard = DuneDashboard.from_dune(dune_connection, args.dashboard_slug)
