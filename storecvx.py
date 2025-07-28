import iris
import pandas as pd

def cvstable():
    conn = None
    cursor = None
    try:
        # Connect to IRIS instance
        conn = iris.connect("127.0.0.1", 1972, "DEMO", "_SYSTEM", "ISCDEMO")
        cursor = conn.cursor()

        # Define SQL for table creation
        create_table_cvx = """
        CREATE TABLE IF NOT EXISTS sql1.cvx_codes (
            cvx_code INT PRIMARY KEY,
            short_description VARCHAR(255),
            full_vaccine_name VARCHAR(512),
            note TEXT,
            vaccine_status VARCHAR(32),
            internal_id INT,
            nonvaccine VARCHAR(5),
            update_date DATE
        )
        """

        # Execute SQL
        cursor.execute(create_table_cvx)
        print("Table 'cvx_codes' created or already exists.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def insert_cvx_codes(csv_path):
    try:
        # Read and clean CSV
        df = pd.read_csv(csv_path)
        df = df.drop(columns=[col for col in df.columns if col.startswith("Unnamed")])

        df.rename(columns={
            "CVX Code": "cvx_code",
            "CVX Short Description": "short_description",
            "Full Vaccine Name": "full_vaccine_name",
            "Note": "note",
            "VaccineStatus": "vaccine_status",
            "internalID": "internal_id",
            "nonvaccine": "nonvaccine",
            "update_date": "update_date"
        }, inplace=True)

        df["nonvaccine"] = df["nonvaccine"].astype(str)  # Convert to VARCHAR-compatible
        df["update_date"] = pd.to_datetime(df["update_date"], errors="coerce").dt.date

        # Connect to IRIS
        conn = iris.connect("127.0.0.1", 1972, "DEMO", "_SYSTEM", "ISCDEMO")
        cursor = conn.cursor()

        insert_sql = """
        INSERT INTO sql1.cvx_codes (
            cvx_code, short_description, full_vaccine_name, note,
            vaccine_status, internal_id, nonvaccine, update_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        for row in df.itertuples(index=False):
            cursor.execute(insert_sql, (
                row.cvx_code,
                row.short_description,
                row.full_vaccine_name,
                row.note if pd.notna(row.note) else None,
                row.vaccine_status,
                row.internal_id,
                row.nonvaccine,
                row.update_date
            ))

        conn.commit()
        print("CVX codes successfully inserted into IRIS.")

    except Exception as e:
        print(f"Error inserting CVX codes: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()




if __name__ == "__main__":
    #cvstable()
    insert_cvx_codes("web_cvx.csv")  # Adjust the path to your CSV file
