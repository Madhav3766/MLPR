import yaml

import pandas as pd

import os

import re  

def extract_number(filename):

    match = re.search(r'\d+', filename)

    if match:

        return int(match.group())

    else:

        return 0


def process_yaml_to_csv(yaml_file_path, csv_file_path, match_id):


    with open(yaml_file_path, 'r') as file:

        yaml_data = yaml.safe_load(file)


    deliveries_data = []



    for inning in yaml_data['innings']:

        for inning_name, inning_details in inning.items():

            match = re.match(r'\d+', inning_name.split(' ')[0])

            if match:

                inning_number = int(match.group())

            else:

                print(f"Skipping inning: {inning_name} in file {yaml_file_path}")

                continue


            batting_team = inning_details['team']

            over_counter = 0

            ball_counter = 0

            current_bowler = None


            for delivery_data in inning_details['deliveries']:

                for ball, details in delivery_data.items():

                    ball_counter += 1


                    if current_bowler is None or current_bowler != details['bowler']:

                        if ball_counter >= 6:

                            over_counter += 1

                            ball_counter = 1

                        current_bowler = details['bowler']


                    ID = f"{match_id}{inning_number}{over_counter:02d}{ball_counter}"


                    delivery = {

                        'ID': ID,

                        'match_id': match_id,

                        'innings': inning_number,

                        'overs': over_counter,

                        'ballnumber': ball_counter,

                        'batter': details['batsman'],

                        'bowler': details['bowler'],

                        'non-striker': details['non_striker'],

                        'extra_type': 'NA' if 'extras' not in details else ', '.join(details['extras'].keys()),

                        'batsman_run': details['runs']['batsman'],

                        'extras_run': details['runs']['extras'],

                        'total_run': details['runs']['total'],

                        'non_boundary': details.get('non_boundary', 0),

                        'isWicketDelivery': 1 if 'wicket' in details else 0,

                        'player_out': 'NA' if 'wicket' not in details else details['wicket'].get('player_out', 'NA'),

                        'kind': 'NA' if 'wicket' not in details else details['wicket'].get('kind', 'NA'),

                        'fielders_involved': 'NA' if 'wicket' not in details else ', '.join(details['wicket'].get('fielders', ['NA'])),

                        'BattingTeam': batting_team

                    }

                    deliveries_data.append(delivery)


    deliveries_df = pd.DataFrame(deliveries_data)

    deliveries_df.to_csv(csv_file_path, index=False)

    print(f"Processed: {yaml_file_path} -> {csv_file_path}")


yaml_dir = '/Users/hemantg/Desktop/ipl (1)'

csv_dir = '/Users/hemantg/Desktop/ball-by-ball-data-5may'


all_matches_df = pd.DataFrame()


yaml_files = sorted(os.listdir(yaml_dir), key=lambda x: extract_number(x))


for yaml_file in yaml_files:

    if yaml_file.endswith('.yaml'):

        match_id = extract_number(yaml_file)

        yaml_file_path = os.path.join(yaml_dir, yaml_file)

        csv_file_path = os.path.join(csv_dir, yaml_file.replace('.yaml', '.csv'))

        match_df = process_yaml_to_csv(yaml_file_path, csv_file_path, match_id)

        all_matches_df = pd.concat([all_matches_df, match_df], ignore_index=True)



combined_csv_path = os.path.join(csv_dir, 'combined_matches.csv')

all_matches_df.to_csv(combined_csv_path, index=False)

print(f"All matches combined into: {combined_csv_path}")

