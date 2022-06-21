"""
Script to load dashboard from configuration file and update.
"""

from duneapi.dashboard import DuneDashboard
from src.dashboard.common import arg_parse

if __name__ == "__main__":
    dune_connection, args = arg_parse(description="Save Dashboard")

    dashboard = DuneDashboard.from_file(
        dune_connection, f"{args.dashboard_slug}/_config.json"
    )
    dashboard.update()
    print("Updated dashboard", dashboard)
