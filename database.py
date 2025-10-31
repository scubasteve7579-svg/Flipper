import os
import json
import pyodbc
from datetime import datetime

# Database connection (adjust SERVER if needed)
conn = pyodbc.connect('DRIVER={SQL Server};SERVER=localhost;DATABASE=flipper;Trusted_Connection=yes')
cursor = conn.cursor()

# Folder path and log file
folder_path = '/Users/stephentaykor/Desktop/flipper_Simulation'
log_file = os.path.join(folder_path, 'database_log.txt')

def log_message(message):
    with open(log_file, 'a') as f:
        f.write(f"{datetime.now()}: {message}\n")
    print(message)

# Step 1: Analyze JSON files to determine structure
json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
if not json_files:
    log_message("No JSON files found in folder.")
    exit()

# Sample first file to infer schema
sample_file = os.path.join(folder_path, json_files[0])
with open(sample_file, 'r') as f:
    sample_data = json.load(f)
    inferred_columns = {key for item in sample_data for key in item.keys()}
    inferred_columns = sorted(list(inferred_columns))  # Unique column names

# Add default columns for Flipper
required_columns = ['item_id', 'title', 'price', 'url', 'categoryPath', 'scraped_at', 'sold', 'sold_price']
all_columns = list(set(required_columns + inferred_columns))
log_message(f"Inferred columns: {all_columns}")

# Step 2: Create or update table
table_name = 'Flipper.Items'
try:
    cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Flipper' AND TABLE_NAME = 'Items'")
    if cursor.fetchone()[0] == 0:
        create_table_sql = f"""
        CREATE TABLE {table_name} (
            {', '.join([f"{col} VARCHAR(255)" for col in all_columns if col not in ['price', 'sold', 'sold_price']]) + ', ' +
             ', '.join([f"price DECIMAL(10, 2)", f"sold BIT DEFAULT 0", f"sold_price DECIMAL(10, 2)"])}
        );
        """
        cursor.execute(create_table_sql)
        log_message(f"Created table {table_name} with columns: {all_columns}")
    else:
        log_message(f"Table {table_name} already exists, proceeding with insert.")
except Exception as e:
    log_message(f"Error creating table: {e}")
    conn.close()
    exit()

# Step 3: Upload all JSON data
total_items = 0
duplicate_items = 0
for filename in json_files:
    file_path = os.path.join(folder_path, filename)
    log_message(f"Processing {filename}...")
    with open(file_path, 'r') as f:
        items = json.load(f)
        for item in items:
            try:
                # Prepare values, defaulting missing fields
                values = [item.get(col, '') for col in all_columns if col not in ['sold', 'sold_price']]
                values.extend([float(item.get('price', 0)) if item.get('price') else 0, 0, None])
                cursor.execute(f"INSERT INTO {table_name} ({', '.join(all_columns)}) VALUES ({', '.join(['?' for _ in all_columns])})", values)
                total_items += 1
            except pyodbc.IntegrityError:
                duplicate_items += 1
                log_message(f"Duplicate item_id skipped in {filename}: {item.get('item_id')}")
            except Exception as e:
                log_message(f"Error inserting item from {filename}: {e}")

# Commit and close
conn.commit()
conn.close()
log_message(f"Upload complete! Total items: {total_items}, Duplicates skipped: {duplicate_items}")