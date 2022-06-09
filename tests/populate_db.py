from tests.db.pg_client import connect

if __name__ == "__main__":
    db_conn = connect()
    cur = db_conn.cursor()
    print("Pre-populating DB for tests...")
    with open("./populate_db.sql", "r", encoding="utf-8") as file:
        populate_query = file.read()

    cur.execute(populate_query)
