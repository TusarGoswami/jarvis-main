import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis.db")

con = sqlite3.connect(DB_PATH)
cursor = con.cursor()

# Create tables if they don't exist
cursor.execute("CREATE TABLE IF NOT EXISTS sys_command(id integer primary key, name VARCHAR(100), path VARCHAR(1000))")
cursor.execute("CREATE TABLE IF NOT EXISTS web_command(id integer primary key, name VARCHAR(100), url VARCHAR(1000))")
cursor.execute("CREATE TABLE IF NOT EXISTS contacts(id integer primary key, name VARCHAR(200), mobile_no VARCHAR(255), email VARCHAR(255) NULL)")

con.commit()
con.close()