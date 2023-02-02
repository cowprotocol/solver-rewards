The system stores all data in a postgres database.
This repo contains the docker image and the flyway migrations to run the database.

## [Optional] Empty Local Instance of Postgres

```sh
docker run -e POSTGRES_PASSWORD=password -p 5432:5432 docker.io/postgres
```

## Perform Migration

Prepare your environment (Database credentials)

```shell
cd internal_transfers/database
cp .env.sample .env
# populate .env with relevant fields
source .env
```

Now, assuming environment variables are in place:

```sh
docker build --tag migration-image .
# Remote DB Instance
docker run --add-host=host.docker.internal:host-gateway --rm migration-image -url=jdbc:postgresql://$POSTGRES_HOST/$POSTGRES_DB -user=$POSTGRES_USER -password=$POSTGRES_PASSWORD migrate
# Local DB Instance (from above)
docker run --network host --add-host=localhost:host-gateway --rm migration-image -url=jdbc:postgresql://$POSTGRES_HOST/$POSTGRES_DB -user=$POSTGRES_USER -password=$POSTGRES_PASSWORD migrate
```

### Troubleshooting

* In case you run into `java.net.UnknownHostException: host.docker.internal`
  add `--add-host=host.docker.internal:host-gateway` right after `docker run`.

* If you're combining a local postgres installation with docker flyway you have to add to the above `--network host` and
  change `host.docker.internal` to `localhost`.

So to test migration with optional local DB described above, use:

```shell
docker run --network host --add-host=localhost:host-gateway --rm migration-image -url=jdbc:postgresql://$POSTGRES_HOST/$POSTGRES_DB -user=$POSTGRES_USER -password=$POSTGRES_PASSWORD migrate
```