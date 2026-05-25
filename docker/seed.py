import os
import sys
import psycopg2

def seed_database():
    # Database connection parameters
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    database = os.environ.get("POSTGRES_DB", "pagila")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")

    print(f"Connecting to PostgreSQL database '{database}' on {host}:{port}...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = True
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        sys.exit(1)

    cursor = conn.cursor()
    print("Amplifying database rows for performance profiling...")

    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_hint_plan;")

        # Create YEAR function for compatibility with Pagila standard queries
        cursor.execute("""
        CREATE OR REPLACE FUNCTION year(ts timestamp) RETURNS integer AS $$
            SELECT EXTRACT(YEAR FROM ts)::integer;
        $$ LANGUAGE sql IMMUTABLE;
        """)

        # Create schema tables if not exist (Sakila/Pagila standard subsets)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer (
            customer_id SERIAL PRIMARY KEY,
            first_name VARCHAR(45) NOT NULL,
            last_name VARCHAR(45) NOT NULL,
            email VARCHAR(50),
            active BOOLEAN DEFAULT TRUE,
            create_date DATE DEFAULT CURRENT_DATE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rental (
            rental_id SERIAL PRIMARY KEY,
            rental_date TIMESTAMP NOT NULL,
            inventory_id INT NOT NULL,
            customer_id INT NOT NULL,
            return_date TIMESTAMP,
            staff_id INT NOT NULL
        );
        """)

        # 1. Seed customer table to >= 50,000 rows
        cursor.execute("SELECT COUNT(*) FROM customer;")
        current_customers = cursor.fetchone()[0]
        if current_customers < 50000:
            to_insert = 50000 - current_customers
            print(f"Seeding {to_insert} customer rows...")
            cursor.execute(f"""
            INSERT INTO customer (first_name, last_name, email, active)
            SELECT 
                'First_' || i,
                'Last_' || i,
                'customer_' || i || '@example.com',
                (i % 2 = 0)
            FROM generate_series(1, {to_insert}) AS i;
            """)

        # 2. Seed rental table to >= 1,000,000 rows
        cursor.execute("SELECT COUNT(*) FROM rental;")
        current_rentals = cursor.fetchone()[0]
        if current_rentals < 1000000:
            to_insert = 1000000 - current_rentals
            print(f"Seeding {to_insert} rental rows...")
            cursor.execute(f"""
            INSERT INTO rental (rental_date, inventory_id, customer_id, return_date, staff_id)
            SELECT 
                NOW() - (random() * INTERVAL '365 days'),
                (random() * 1000)::INT + 1,
                (random() * 50000)::INT + 1,
                NOW() - (random() * INTERVAL '300 days'),
                (random() * 5)::INT + 1
            FROM generate_series(1, {to_insert}) AS i;
            """)

        # Validation assertions
        cursor.execute("SELECT COUNT(*) FROM customer;")
        final_customers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rental;")
        final_rentals = cursor.fetchone()[0]

        print(f"Verification: customer count = {final_customers:,} (Target: >= 50,000)")
        print(f"Verification: rental count = {final_rentals:,} (Target: >= 1,000,000)")

        if final_customers < 50000 or final_rentals < 1000000:
            raise ValueError("Seed validation failed: Row count requirements not met!")

        print("✔ Seeding and data amplification completed successfully.")
        
    except Exception as e:
        print(f"Seeding process failed: {str(e)}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    seed_database()
