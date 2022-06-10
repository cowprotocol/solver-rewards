import unittest

from tests.db.pg_client import connect


class TestMockDB(unittest.TestCase):
    def test_db_connect(self):
        """
        This is just an example test demonstrating that we have connection
        with read and write access to the test database
        """
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
            "Farm",
            "Face",
            37,
            "Farmville",
            "farm@fa.ce",
        ]

        insert = """
            INSERT INTO student(firstname, lastname, age, address, email) 
            VALUES(%s, %s, %s, %s, %s) RETURNING *
        """.format(
            values
        )

        cur.execute(table)
        cur.execute(insert, values)
        # Its weird the way `values` is used twice here!

        cur.execute("SELECT * FROM student")
        x = cur.fetchall()
        self.assertEqual(1, len(x))


if __name__ == "__main__":
    unittest.main()
