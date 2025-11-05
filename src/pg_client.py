"""Basic client for connecting to postgres database with login credentials"""

from __future__ import annotations

import pandas as pd
from pandas import DataFrame, Series, read_sql_query
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config import AccountingConfig
from src.logger import set_log
from src.models.accounting_period import AccountingPeriod

log = set_log(__name__)


class MultiInstanceDBFetcher:
    """
    Allows identical query execution on multiple db instances (merging results).
    Currently very specific to the CoW Protocol Orderbook DB.
    """

    def __init__(self):
        log.info("Initializing MultiInstanceDBFetcher")

    @classmethod
    def exec_query(cls, query: str, engine: Engine) -> DataFrame:
        """Executes query on DB engine"""
        return pd.read_sql(sql=query, con=engine)

    def get_analytics_db_table_prod_and_barn(
        self,
        table_name: str,
        accounting_period: AccountingPeriod,
        config: AccountingConfig,
    ) -> DataFrame:
        # pylint: disable=too-many-locals
        """
        Constructs and executes a query on an analytics database for specific environments
        and consolidates the results into a single DataFrame. The function fetches data
        from multiple database environments (`prod`, `staging`) for a given accounting
        period and specified table, combining rows from each environment into a
        unified Pandas DataFrame.

        Parameters
        ----------
        table_name : str
            The name of the database table to query.
        accounting_period : AccountingPeriod
            The period for which the data should be fetched. The AccountingPeriod
            object must have `start` and `end` attributes formatted as datetime
            objects.
        config : AccountingConfig
            Configuration object containing database connection details such as
            analytics_db_url, network_db_name, and schema.

        Returns
        -------
        DataFrame
            A Pandas DataFrame containing the concatenated query results from the
            `prod` and `staging` environments.
        """
        db_url = (
            config.orderbook_config.analytics_db_url
        )  # this is not compatible with the current format
        network = config.orderbook_config.network_db_name
        schema = config.orderbook_config.schema
        start_time_string = accounting_period.start.strftime("%Y-%m-%d %H:%M:%S")
        end_time_string = accounting_period.end.strftime("%Y-%m-%d %H:%M:%S")
        accounting_period_string = f"{start_time_string} - {end_time_string}"
        query = f"""SELECT * FROM {schema}.{table_name}
        where accounting_period = '{accounting_period_string}'"""
        result_list = []
        # for environment in ["prod"]:
        for environment in ["prod", "staging"]:
            pg_engine = create_engine(
                f"postgresql+psycopg2://{db_url}/{environment}_{network}",
                pool_pre_ping=True,
                connect_args={
                    "keepalives": 1,
                    "keepalives_idle": 30,
                    "keepalives_interval": 10,
                    "keepalives_count": 5,
                },
            )
            with pg_engine.connect() as conn:
                result = read_sql_query(
                    query,
                    conn,
                )
                result_list.append(result)

        results = pd.concat(result_list).reset_index(drop=True)

        return results

    def get_data_per_solver(
        self, accounting_period: AccountingPeriod, config: AccountingConfig
    ) -> DataFrame:
        """Fetches and processes solver-related data for a specific accounting period.

        This function retrieves data for a given accounting period and configuration by
        querying the prod and barn database. The results are
        then processed to convert specific columns (e.g., solver, pool_address, and
        reward_target) from bytearray format to hexadecimal format for standardized
        representation.

        Parameters
        ----------
        accounting_period : AccountingPeriod
            The accounting period object used to filter data for the required time range.
        config : AccountingConfig
            Configuration detailing settings and parameters for the data retrieval and
            processing operations.

        Returns
        -------
        DataFrame
            A DataFrame containing processed data for each solver, with specific fields
            converted to hexadecimal format for appropriate representation.
        """
        results = self.get_analytics_db_table_prod_and_barn(
            "fct_data_per_solver_and_accounting_period", accounting_period, config
        )

        hex_columns = ["solver", "pool_address", "reward_target"]
        for column in hex_columns:
            results[column] = results[column].apply(bytearray2hex)

        return results

    def get_partner_and_protocol_fees(
        self, accounting_period: AccountingPeriod, config: AccountingConfig
    ) -> DataFrame:
        """
        Fetches and processes partner and protocol fees data from an analytics database table.

        This function retrieves data related to partner and protocol fees for a specified
        accounting period and configuration. The data is fetched from the analytics database
        production and barn tables. Additionally, the function processes specific columns to
        convert byte data into hexadecimal format for further usage.

        Parameters
        ----------
        accounting_period : AccountingPeriod
            The accounting period for which the partner and protocol fees data is to be fetched.
        config : AccountingConfig
            Configuration settings specifying the analytics database and environment.

        Returns
        -------
        DataFrame
            A Pandas DataFrame containing the fetched and processed partner and protocol
            fees data. Specific columns in this DataFrame have been converted into
            hexadecimal format.
        """
        results = self.get_analytics_db_table_prod_and_barn(
            "fct_partner_and_protocol_fees", accounting_period, config
        )

        hex_columns = ["partner_fee_recipient"]
        for column in hex_columns:
            results[column] = results[column].apply(bytearray2hex)

        return results


def bytearray2hex(address: bytearray) -> str | None:
    """Converts a bytearray into its hexadecimal string representation.

    This function takes a bytearray input and transforms it into a
    string representation of its hexadecimal value, prefixed with "0x".
    If the input bytearray is empty, the original value is returned.

    Parameters
    ----------
    address : bytearray
        The bytearray to be converted into a hexadecimal string.

    Returns
    -------
    str
        A string representing the hexadecimal equivalent of the input
        bytearray, prefixed with "0x". If the bytearray is empty, the
        original `address` is returned.
    """
    return "0x" + address.hex() if address else None


def pg_hex2bytea(hex_address: str) -> str:
    """
    transforms hex string (beginning with 0x) to dune
    compatible bytea by replacing `0x` with `\\x`.
    """
    return hex_address.replace("0x", "\\x")


def log_duplicate_rows(df: DataFrame) -> None:
    """Log rows with duplicate solvers entries.
    Printing defaults are changed to show all column entries."""
    duplicated_entries = df[df["solver"].duplicated(keep=False)]
    with pd.option_context(
        "display.max_columns",
        None,
        "display.width",
        None,
        "display.max_colwidth",
        None,
    ):
        log.warning(
            f"Solvers found in both environments:\n {duplicated_entries}.\n"
            "Merging results."
        )


def merge_lists(series: Series) -> list | None:
    """Merges series containing lists into large list.
    Returns None if the result would be an empty list."""
    merged = []
    for lst in series:
        if lst is not None:
            merged.extend(lst)
    return merged if merged else None
