"""
Script to generate the CSV Airdrop file for Solver Rewards over an Accounting Period
"""
from __future__ import annotations

import os
import ssl
from dataclasses import asdict

import certifi
from dune_client.file.interface import FileIO
from eth_typing.ethpm import URI
from gnosis.eth.ethereum_client import EthereumClient
from slack.web.client import WebClient

from src.constants import (
    SAFE_ADDRESS,
    NETWORK,
    NODE_URL,
    AIRDROP_URL,
    SAFE_URL,
    FILE_OUT_DIR,
    DOCS_URL,
)
from src.fetch.payouts import construct_payouts
from src.models.accounting_period import AccountingPeriod
from src.models.transfer import Transfer, CSVTransfer
from src.multisend import post_multisend, prepend_unwrap_if_necessary
from src.pg_client import MultiInstanceDBFetcher
from src.slack_utils import post_to_slack
from src.utils.print_store import Category, PrintStore
from src.utils.script_args import generic_script_init


def manual_propose(transfers: list[Transfer], period: AccountingPeriod) -> None:
    """
    Entry point to manual creation of rewards payout transaction.
    This function generates the CSV transfer file to be pasted into the COW Safe app
    """
    print(
        f"Please double check the batches with unusual slippage: "
        f"{period.unusual_slippage_url()}"
    )
    csv_transfers = [asdict(CSVTransfer.from_transfer(t)) for t in transfers]
    FileIO(FILE_OUT_DIR).write_csv(csv_transfers, f"transfers-{period}.csv")

    print(Transfer.summarize(transfers))
    print(
        f"Please cross check these results with the dashboard linked above.\n "
        f"For solver payouts, paste the transfer file CSV Airdrop at:\n"
        f"{AIRDROP_URL}"
    )


def auto_propose(
    transfers: list[Transfer],
    log_saver: PrintStore,
    slack_client: WebClient,
    dry_run: bool,
) -> None:
    """
    Entry point auto creation of rewards payout transaction.
    This function encodes the multisend of reward transfers and posts
    the transaction to the COW TEAM SAFE from the proposer account.
    """
    # Check for required env vars early
    # so not to wait for query execution to realize it's not available.
    signing_key = os.environ["PROPOSER_PK"]
    client = EthereumClient(URI(NODE_URL))

    log_saver.print(Transfer.summarize(transfers), category=Category.TOTALS)
    transactions = prepend_unwrap_if_necessary(
        client, SAFE_ADDRESS, transactions=[t.as_multisend_tx() for t in transfers]
    )
    if len(transactions) > len(transfers):
        log_saver.print("Prepended WETH unwrap", Category.GENERAL)

    log_saver.print(
        f"Instructions for verifying the payout transaction can be found at\n{DOCS_URL}",
        category=Category.GENERAL,
    )

    if not dry_run:
        nonce = post_multisend(
            safe_address=SAFE_ADDRESS,
            transactions=transactions,
            network=NETWORK,
            signing_key=signing_key,
            client=client,
        )
        post_to_slack(
            slack_client,
            channel=os.environ["SLACK_CHANNEL"],
            message=(
                f"Solver Rewards transaction with nonce {nonce} pending signatures.\n"
                f"To sign and execute, visit:\n{SAFE_URL}\n"
                f"More details in thread"
            ),
            sub_messages=log_saver.get_values(),
        )


if __name__ == "__main__":
    args = generic_script_init(description="Fetch Complete Reimbursement")
    dune = args.dune
    dune.log_saver.print(
        f"The data aggregated can be visualized at\n{dune.period.dashboard_url()}",
        category=Category.GENERAL,
    )

    payout_transfers_temp = construct_payouts(
        args.dune,
        orderbook=MultiInstanceDBFetcher(
            [os.environ["PROD_DB_URL"], os.environ["BARN_DB_URL"]]
        ),
    )
    payout_transfers = []
    for tr in payout_transfers_temp:
        if tr.token is None:
            if tr.amount_wei > args.min_transfer_amount_wei:
                payout_transfers.append(tr)
        else:
            if tr.amount_wei > args.min_transfer_amount_cow_atoms:
                payout_transfers.append(tr)

    if args.consolidate_transfers:
        payout_transfers = Transfer.consolidate(payout_transfers)

    if args.post_tx:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        auto_propose(
            transfers=payout_transfers,
            log_saver=dune.log_saver,
            slack_client=WebClient(
                token=os.environ["SLACK_TOKEN"],
                # https://stackoverflow.com/questions/59808346/python-3-slack-client-ssl-sslcertverificationerror
                ssl=ssl_context,
            ),
            dry_run=args.dry_run,
        )
    else:
        manual_propose(transfers=payout_transfers, period=dune.period)
