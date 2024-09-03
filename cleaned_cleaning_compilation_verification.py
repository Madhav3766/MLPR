import os
import pandas as pd
directory = "/Users/hemantg/Documents/improve-accuracy-mlpr-csv"  for filename in os.listdir(directory):
    if filename.endswith(".csv"):
        file_path = os.path.join(directory, filename)
        df = pd.read_csv(file_path)
        file_number = filename.split("-")[0].strip()
        df[""] = file_number
        df.to_csv(file_path, index=False)
import csv
with open('/Users/hemantg/Desktop/our-algo.csv', 'r') as file:
    reader = csv.DictReader(file)
    match_id_counts = {}
    for row in reader:
        match_id = row['match_id']
        match_id_counts[match_id] = match_id_counts.get(match_id, 0) + 1
    for match_id, count in match_id_counts.items():
        print(f"match_id {match_id} has {count} rows")
import csv
with open('/Users/hemantg/Documents/our-algo.csv', 'r') as file:
    reader = csv.DictReader(file)
    match_id_roles = {}
    for row in reader:
        match_id = row['match_id']
        role = row['role']
        if match_id not in match_id_roles:
            match_id_roles[match_id] = set()
        match_id_roles[match_id].add(role)
    missing_roles = {}
    required_roles = set(['WK', 'AR', 'BWL', 'BAT'])
    for match_id, roles in match_id_roles.items():
        missing = required_roles - roles
        if missing:
            missing_roles[match_id] = missing
    if missing_roles:
        print("The following match_id values are missing some roles:")
        for match_id, missing in missing_roles.items():
            print(f"match_id {match_id} is missing roles: {', '.join(missing)}")
    else:
        print("All match_id values have the required roles.")
import os
import pandas as pd
import re
directory = "/Users/hemantg/Downloads/try-pnc-4"  for filename in os.listdir(directory):
    if filename.endswith(".csv"):
        file_path = os.path.join(directory, filename)
        df = pd.read_csv(file_path)
        match = re.search(r'game_(\d+)_', filename)
        if match:
            file_number = match.group(1)
        else:
            file_number = "Unknown"
        df["file_number"] = file_number
        df.to_csv(file_path, index=False)
import os
import pandas as pd
import re
original_directory = "/Users/hemantg/Downloads/try-pnc-4"
output_directory = "/Users/hemantg/Downloads/combined-pnc-4"
def get_file_type(filename):
    match = re.search(r'(\d+) - (\d+)', filename)
    if match:
        return f"{match.group(1)} - {match.group(2)}"
    else:
        return "Unknown"
file_type_data = {}
for filename in os.listdir(original_directory):
    if filename.endswith(".csv"):
        file_path = os.path.join(original_directory, filename)
        df = pd.read_csv(file_path)
        file_type = get_file_type(filename)
        if file_type in file_type_data:
            file_type_data[file_type].append(df)
        else:
            file_type_data[file_type] = [df]
os.makedirs(output_directory, exist_ok=True)
for file_type, dfs in file_type_data.items():
    combined_df = pd.concat(dfs, ignore_index=True)
    combined_df = combined_df.sort_values(by='file_number')      output_filename = f"{file_type}.csv"
    output_path = os.path.join(output_directory, output_filename)
    combined_df.to_csv(output_path, index=False)
import os
import pandas as pd
directory = "/Users/hemantg/Downloads/combined-pnc-4"
for filename in os.listdir(directory):
    if filename.endswith(".csv"):
        file_path = os.path.join(directory, filename)
        df = pd.read_csv(file_path)
        num_rows = len(df)
        print(f"File: {filename} - Number of rows: {num_rows}")
import os
import pandas as pd
directory = '/Users/hemantg/Downloads/combined-pnc-4'
for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        file_path = os.path.join(directory, filename)
        df = pd.read_csv(file_path)
        if 'file_number' in df.columns:
            df = df.rename(columns={'file_number': 'match_id'})
            df.to_csv(file_path, index=False)
            print(f"Column renamed in {filename}")
        else:
            print(f"Column 'file_number' not found in {filename}")
import os
import pandas as pd
directory = '/Users/hemantg/Downloads/combined-pnc-4 wo-fantasy-score'
for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        file_path = os.path.join(directory, filename)
        df = pd.read_csv(file_path)
        if 'Fantasy Score' in df.columns:
            df = df.drop('Fantasy Score', axis=1)
            df.to_csv(file_path, index=False)
            print(f"Removed 'Fantasy Score' column from {filename}")
        else:
            print(f"'Fantasy Score' column not found in {filename}")