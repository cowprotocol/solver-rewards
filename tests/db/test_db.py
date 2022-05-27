import unittest

from tests.db.pg_client import connect


class TestMockDB(unittest.TestCase):
    def test_db_connect(self):
        db_conn = connect()
        cur = db_conn.cursor()

        table = """
            CREATE TABLE student(
                id SERIAL PRIMARY KEY, 
                firstName VARCHAR(40) NOT NULL, 
                lastName VARCHAR(40) NOT NULL, 
                age INT, 
                address VARCHAR(80), 
                email VARCHAR(40)
            )
        """
        values = [
            "Ben",
            "Smith",
            37,
            "Berlin, Germany",
            "bh2smith@gmail.com",
        ]

        insert = """
            INSERT INTO student(firstname, lastname, age, address, email) 
            VALUES(%s, %s, %s, %s, %s) RETURNING *
        """.format(
            values
        )

        cur.execute(table)
        cur.execute(insert, values)
        # Its weird the way values is used twice here!

        cur.execute("SELECT * FROM student")
        x = cur.fetchall()
        self.assertEqual(1, len(x))

    def test_db_pre_populated(self):
        db_conn = connect()
        cur = db_conn.cursor()

        # with open("tests/populate_db.sql", "r", encoding="utf-8") as file:
        #     populate_query = file.read()

        # cur.execute(populate_query)
        cur.execute("SELECT * FROM erc20.\"ERC20_evt_Transfer\" LIMIT 100")
        x = cur.fetchall()
        self.assertEqual(100, len(x))


if __name__ == "__main__":
    unittest.main()
