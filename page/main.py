import mysql.connector
from mysql.connector import Error

from db import DB_CONFIG

# Kept only as a command-line connection check. Runtime pages use db.py.
DB_config = DB_CONFIG

def test_connection():
    print("testting to connect")
    conn = None
    try:
        conn = mysql.connector.connect(**DB_config)

        if conn.is_connected():
            db_info = conn.get_server_info()
            print(f"successful connect,version:{db_info}")

    except Error as e:
        print("not succese connect",e)

    finally:
        if conn and conn.is_connected():
            conn.close()
            print("connection closed")



if __name__== "__main__":
    test_connection()
