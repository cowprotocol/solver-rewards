# CoW Protocol: Solver Reimbursement & Rewards Distributor

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Installation & Usage

```shell
python3 -m venv env
source ./env/bin/activate
pip install -r requirements.txt
cp .env.sample .env    <----- Copy your Dune credentials here!
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
python -m src.fetch.period_totals --start '2022-02-01'
```

This will result in the following console logs:

```
PeriodTotals(period=<src.models.AccountingPeriod object at 0x7f21bd9ad600>,
             execution_cost_eth=148,
             cow_rewards=423400,
             realized_fees_eth=92)
```

To fetch the total slippage for an accounting period, run period_slippage script as follows:

```shell
python -m src.fetch.period_slippage --start '2022-02-01'
```

# Summary of Accounting Procedure

In what follows **Accounting Periods** are defined in intervals of 1 week and accounting
is performed on the time interval

```
StartTime <= block_time < EndTime
```

# Testing & Contributing

To run the unit, end to end and full test suite run any of

```shell
python -m pytest tests/unit/
python -m pytest tests/e2e/
python -m pytest tests/
```

This project conforms to [Black](https://github.com/psf/black) code style.
You can auto format the project with the following command:

```shell
black ./
```

However, many IDEs can be configured to auto format on save.

## Proposed Reimbursement Work Flow

The solver reimbursements are to be executed each Tuesday with the accounting period of the last 7 days. If the payout can not be done on Tuesdays, its okay to execute them later, but still the accounting period should always be from 00:00 between Monday and Tuesday to 00:00 between Monday and Tuesday

In order to do the payout, run the following scripts:
```shell
rm -r out/
python -m src.fetch.transfer_file --start '2022-MM-DD'
```
Here, the start should specify the Tuesday of the start of the accounting period. The next Tuesday - the end date of the accounting period - will be calculated automatically by the script.
I.e. for the first payout, we would run:
```shell
python -m src.fetch.transfer_file --start '2022-03-01'
```
and for the next one:
```shell
python -m src.fetch.transfer_file --start '2022-03-08'
```


Please double-check that the payout is reasonable. That means the eth sent should be between 30-80 ETH, depending on gas prices from last week. Also the amount of cow send should reflect 100x the amount of batches. Reasonable COW totals are around 300000-500000, that means 500-700 batches a day.

Also, it might happen that the slippage of a solver is bigger than the ETH payout. In this case, please do not proceed with the payout, until the root cause is known. Feel free to reach out the project maintainers to do the investigation.

Note that we must wait some time after the period has ended for some data to finalize (e.g. `prices.usd`, `ethereum.transactions` our event data, etc...). Hence, the scripts should not be executed immediately after the accounting period has ended.

After generating the transfer file and double-checking the results, please create the multi-send transaction with the link provided in the console.

Inform the team of this proposed transaction in the #dev-multisig Slack channel and follow through to ensure execution. It is preferred that the transaction be executed by the proposer account(eth:0xd8Ca5FE380b68171155C7069B8df166db28befdd).


## Docker

This project has a strict requirement of python >= 3.10 which may not be common version for most operating systems. 
In order to make the reimbursement effort seamless, we have prepared the following docker container.

```shell
docker pull ghcr.io/cowprotocol/solver-rewards
# Prepare environment variables
cp .env.sample .env  # Fill in your Dune Credentials
# Run
docker run -it --rm --env-file .env -v $(PWD):/app/out ghcr.io/cowprotocol/solver-rewards --start 'YYYY-MM-DD'
```

and (usually after about 30 seconds) find the transfer file written to your current working directory.
