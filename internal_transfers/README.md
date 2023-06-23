# Internal Transfers

## Motivation & Summary

Internal Settlements have been a challenge to evaluate slippage since some information
required for the computation never winds up on chain.
Specifically, when the driver decides to internalize an interaction provided by a solver,
the interaction is excluded from the settlement call data.
In order to recover this data we must make token transfers (or imbalances) from
internalized interactions transparently available for consumption.

This project replaces the subquery
[buffer_trades](https://github.com/cowprotocol/solver-rewards/blob/c7e9c85706decb1a1be28d639ee34e35646bca50/queries/dune_v2/period_slippage.sql#L239-L309)
(an approximation for internal interactions implemented purely within Dune Analytics) with the actual internalized data.

In brief, the project consists of a Data Pipeline implementing the following flow;

1. WebHook/Event Listener for CoW Protocol Settlement Events emitted
   by [CoW Protocol: GPv2Settlement](https://etherscan.io/address/0x9008d19f58aabd9ed0d60971565aa8510560ab41)
2. Settlement Events trigger an ETL Pipeline that
    - Fetches full/unoptimized call data provided by the solver for the winning settlement from
      the [Orderbook API](https://api.cow.fi/docs/#)
    - Simulates the full call data extracting and classifying transfers from event logs
    - Evaluates the `InternalizedLedger` as the difference `FullLedger - ActualLedger`
3. Finally, the `InternalizedLedger` from step 2 is written to a [Database](./database/README.md) and later synced into
   Dune community sources.

For more Details on each component outlined above please visit respective readmes:

## [Webhook] Tenderly Actions

Documentation: https://tenderly.co/web3-actions
Requirements: [Tenderly CLI](https://github.com/Tenderly/tenderly-cli)

actions directory was scaffolded and deployed as follows:

```shell
tenderly actions init --language typescript
tenderly actions deploy
```

## Generate Database Schema

Following this article on [Postgres with Typescript](https://www.atdatabases.org/docs/pg-guide-typescript) we can
generate the schema
From within `actions/`

```shell
source 
 export DB_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}
npx @databases/pg-schema-cli --database $DB_URL --directory src/__generated__
```


## Build and Deploy Lambda Function

Using env vars specified in .env.lambda

### Build Container Image
```shell
cd actions
 export IMAGE_NAME=internal-transfers
docker build -t ${IMAGE_NAME} .
```

Run locally with 
```shell
docker run -p 9000:8080 \
  --env NODE_URL=$NODE_URL \
  --env DATABASE_URL=$DATABASE_URL \
  --env TENDERLY_ACCESS_KEY=$TENDERLY_ACCESS_KEY \
  ${IMAGE_NAME}
```
this will have `FUNCTION_URL=http://localhost:9000/2015-03-31/functions/function/invocations` to which you can post:

```shell
curl -XPOST ${FUNCTION_URL} -d '{"txHash": "0x42"}'
```

### Publish Container Image

```shell
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_URL}
aws ecr create-repository --repository-name ${IMAGE_NAME} --region ${AWS_REGION} --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE
docker tag ${IMAGE_NAME}:latest ${AWS_URL}/${IMAGE_NAME}:latest & docker push ${AWS_URL}/${IMAGE_NAME}:latest 
```

## Create Lambda from Image

Via AWS Console this can now be selected. 
In the configuration settings,
- Set relevant _environment variables_ (in our case this is `NODE_URL`, `DATABASE_URL` and `TENDERLY_ACCESS_KEY`)
- enable `functionURL` 

Once the `functionURL` is acquired try to invoke it as follows:

```shell
 export FUNCTION_URL=
curl -XPOST \
      ${FUNCTION_URL} \
      -H 'content-type: application/json' \
      -d '{"txHash": "YourFavouriteSettlementTransactionHash"}'
```
