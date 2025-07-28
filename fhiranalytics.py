import iris

# Connect to IRIS instance
conn = iris.connect("127.0.0.1", 1972, "DEMO", "_SYSTEM", "ISCDEMO")

# Open a cursor and run SQL
cursor = conn.cursor()
cursor.execute("SELECT * FROM sql1.Patient")

# Fetch and print
for row in cursor.fetchall():
    print(row)

cursor.close()
conn.close()