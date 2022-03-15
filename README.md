# CoW Protocol: Solver Reimbursement & Rewards Distributor

## Installation & Usage

```shell
python3 -m venv env
source ./env/bin/activate
pip install -r requirements.txt
cp .env.sample .env
source .env
```

Fill out your Dune credentials in the `.env` file. The Dune user and password are
straight-forward login credentials to Dune Analytics. The `DUNE_QUERY_ID` is an integer
id found in the URL of a query when saved in the Dune interface. This should be created
beforehand, but the same query id can be used everywhere throughout the program (as long
as it is owned by the account corresponding to the user credentials provided).

Each individual file should be executable as a standalone script. Many of the scripts
found here initiate and execute query, returning the results.

Example script

To fetch the total eth spent, realized fees and cow rewards for an accounting period run
the period totals script as follows

```shell
python -m src.fetch.period_totals --start '2022-02-01' --end '2022-02-08'
```

This will result in the following console logs:

```
Fetching Accounting Period Totals on Network.MAINNET...
got 1 records from last query
PeriodTotals(period_start=datetime.datetime(2022, 2, 1, 0, 0),
             period_end=datetime.datetime(2022, 2, 8, 0, 0),
             execution_cost_eth=148.2367050858087,
             cow_rewards=423400,
             realized_fees_eth=92.69632712493294)
```

To fetch the total slippage for an accounting period, run period_slippage script as follows:

```shell
python -m src.fetch.period_slippage --start '2022-02-01' --end '2022-02-08'
```
# Summary of Accounting Procedure

In what follows **Accounting Periods** are defined in intervals of 1 week and accounting
is performed on the time interval

```
StartTime <= block_time < EndTime
```

## Proposed Reimbursement Work Flow

The proposed workflow is to be automated and run on a schedule of once per *accounting
period* at N hours past the end of the accounting period. Note that we must wait some
time after the period has ended for some data to finalize (e.g. `dex.trades`
, `ethereum.transactions` our event data, etc...).

1. Run the Reimbursement & Rewards Query

2. Compute Solver Imbalances (i.e. penalties)
    - Purely Internal Balances are cross-checked with accepted internally traded tokens
      list
    - Slippage Imbalances

3. Run the Fee Withdraw and Convert Service (if ETH is needed)

4. Run the Disbursement Script This script fetches Reimbursement & Rewards table in the
   form of a CSV Airdrop Transfer file then initiates/proposes a multi-send Transaction
   to CoW DAO Safe. The only manual interaction then needed here is to sign and execute
   the automatically proposed reimbursement transaction.

In what follows below the Execution Costs and Reimbursements (displayed above and to the
right) are currently a work in progress on accounting for individual solver's internal (
Settlement Contract) balances. This can be made accurate on a per-token basis, but USD
valuations are rely on third party price feeds.
