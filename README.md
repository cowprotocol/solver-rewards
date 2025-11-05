# CoW Protocol: Solver Accounting

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Installation & Usage (Quickstart)

```shell
make install
cp .env.sample .env    <----- Copy your Dune and orderbook credentials here!
```

Fill out your Dune credentials in the `.env` file.

Generate the solver-payouts with for the accounting period 7 days (with today as end date).

```shell
python -m src.fetch.transfer_file
```

To generate order data for the current month to upload to Dune run the following command.

```shell
python -m src.data_sync.sync_data --sync-table order_data
```

For more advanced usage of these scripts see below.

# Summary of Accounting Procedure

In what follows **Accounting Periods** are defined in intervals of 1 week and accounting
is performed on the time interval

```
StartTime <= block_time < EndTime
```

# Testing & Contributing

## Testing

To run the unit tests

```shell
make test-unit
```

To run the query tests, you must first have a local instance of the database running

```shell
docker build -t test_db -f Dockerfile.db .
docker run -d --name testDB -p 5432:5432 test_db
python -m pytest tests/queries/
```

or just

```shell
make test-db
```

If you have the local database running you can run the entire suite of tests with

```shell
python -m pytest tests/
```

This project conforms to [Black](https://github.com/psf/black) code style.
You can auto format the project with the following command:

```shell
black ./
```

However, many IDEs can be configured to auto format on save.

## Advanced Payout Generation

looking at the script help menu can help provide a list of options!

```shell
$  python -m src.fetch.transfer_file --help 

usage: Fetch Complete Reimbursement [-h] [--start START] [--post-tx] [--dry-run]

options:
  -h, --help            show this help message and exit
  --start START         Accounting Period Start. Defaults to previous Tuesday
  --post-tx     Flag indicating whether multisend should be posted to safe (requires valid env var `PROPOSER_PK`)
  --dry-run     Flag indicating whether script should not post alerts or transactions.
  --ignore-slippage
                        Ignore slippage computations
```

The solver reimbursements are executed each Tuesday with the accounting period of the last 7 days.
The default accounting period is 7 days with end date equal to the current date.
If the payout script can not be run on Tuesday, one will have to specify the start date to specify the correct
accounting period.

To generate the CSV Transfer file manually run the "quickstart" variant of the script.
A more fine-tuned variant of the script execution could look like this:

```shell
python -m src.fetch.transfer_file --start 2023-03-14 --post-tx True
```

which would run for the accounting period March 14 - 21, 2023, using the Post CIP-20 reward scheme and post the payout
transaction directly to the safe (i.e. without generating a CSV file).

## Validating the Payout Transaction

Please visit this [Notion document](https://www.notion.so/cownation/Solver-Payouts-3dfee64eb3d449ed8157a652cc817a8c).
In particular
see [Validation by Example](https://www.notion.so/cownation/Solver-Payouts-3dfee64eb3d449ed8157a652cc817a8c?pvs=4#5a99004c03714f939cd80ef41a3d9590)
section.

### Additional Notes

Also, it might happen that the slippage of a solver is bigger than the ETH payout. In this case, please do not proceed
with the payout, until the root cause is known. Feel free to reach out the project maintainers to do the investigation.

Note that we must wait some time after the period has ended for some data to finalize (
e.g. `prices.usd`, `ethereum.transactions` our event data, etc...). Hence, the scripts should not be executed
immediately after the accounting period has ended.

After generating the transfer file and double-checking the results, please create the multi-send transaction with the
link provided in the console.

Inform the team of this proposed transaction in the #dev-multisig Slack channel and follow through to ensure execution.
It is preferred that the transaction be executed by the proposer account(eth:
0xd8Ca5FE380b68171155C7069B8df166db28befdd).

## Docker

This project has a strict requirement of python >= 3.10 which may not be common version for most operating systems.
In order to make the reimbursement effort seamless, we have prepared the following docker container.

```shell
# Prepare environment variables
cp .env.sample .env  # Fill in your Dune Credentials
# Run (always ensuring latest version is being used).
docker run --pull=always -it --rm \
  --env-file .env \
  -v $PWD:/app/out \
  ghcr.io/cowprotocol/solver-rewards:main \
  src.fetch.transfer_file \
  --start 'YYYY-MM-DD'
```

and (usually after about 30 seconds) find the transfer file written to your current working directory.

# Managing Dependencies
Python libraries can be added to the `requirements.in` file. After this `pip-compile` or `python -m pip-compile` will update the `requirements.txt` for you (you may have to install the libry manually first). 
Warning: this might take a long time for large changes or when you run pip-compile for the first time. Running the command with the `-v` flag can help keep track of what's happening.
