# Taken from:
# https://dev.to/andre347/how-to-easily-create-a-postgres-database-in-docker-4moj
# Build: 
#   docker build -t test_db .
# Run: 
#   docker run -d --name testDB -p 5432:5432 test_db
# Test:
#   python -m pytest tests/db 
FROM postgres
ENV POSTGRES_PASSWORD postgres
ENV POSTGRES_DB postgres
COPY . /repo
COPY populate_db.sql /docker-entrypoint-initdb.d/