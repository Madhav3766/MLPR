import yaml

import pandas as pd

import os

from datetime import datetime, date


def calculate_margin_and_won_by(innings, match_info):

    if match_info['toss']['decision'] == 'bat':

        batting_first = match_info['toss']['winner']

    else:

        batting_first = match_info['teams'][0] if match_info['teams'][1] == match_info['toss']['winner'] else match_info['teams'][1]


    team1_runs, team2_runs, team2_wickets_lost = 0, 0, 0

    for inning in innings:

        for inning_name, inning_details in inning.items():

            for delivery in inning_details['deliveries']:

                for delivery_number, delivery_data in delivery.items():

                    runs = delivery_data['runs']['total']

                    if inning_details['team'] == batting_first:

                        team1_runs += runs

                    else:

                        team2_runs += runs

                        if 'wicket' in delivery_data:

                            team2_wickets_lost += 1


    if team1_runs == team2_runs:

        return 'SuperOver', 'NA'

    if 'outcome' in match_info and 'winner' in match_info['outcome']:

        winning_team = match_info['outcome']['winner']

        if winning_team == batting_first:

            return 'runs', team1_runs - team2_runs

        else:

            return 'wickets', 10 - team2_wickets_lost  
    else:

        return 'No result', 'NA'


def extract_team_players(innings, team):

    players = []

    for inning in innings:

        for inning_details in inning.values():

            if inning_details['team'] == team:

                for delivery in inning_details['deliveries']:

                    delivery_info = list(delivery.values())[0]

                    if delivery_info['batsman'] not in players:

                        players.append(delivery_info['batsman'])

                    if delivery_info['non_striker'] not in players:

                        players.append(delivery_info['non_striker'])

                    if delivery_info['bowler'] not in players:

                        players.append(delivery_info['bowler'])

    return players


def extract_match_data(yaml_file_path, season_tracker, match_number_tracker):

    with open(yaml_file_path, 'r') as file:

        yaml_data = yaml.safe_load(file)


    match_info = yaml_data['info']

    date_value = match_info['dates'][0]

    date_value = date_value if isinstance(date_value, date) else datetime.strptime(date_value, '%Y-%m-%d').date()

    season_year = date_value.year

    season = season_tracker.setdefault(season_year, len(season_tracker) + 1)

    match_number_tracker.setdefault(season_year, 0)

    match_number_tracker[season_year] += 1

    match_number = match_number_tracker[season_year]


    won_by, margin = calculate_margin_and_won_by(yaml_data['innings'], match_info)


    match_data = {

        'ID': os.path.basename(yaml_file_path).split('.')[0],

        'City': match_info.get('city', 'NA'),

        'Date': date_value.strftime('%Y-%m-%d'),

        'Season': season,

        'MatchNumber': match_number,

        'Team1': match_info['teams'][0],

        'Team2': match_info['teams'][1],

        'Venue': match_info.get('venue', 'NA'),

        'TossWinner': match_info['toss']['winner'],

        'TossDecision': match_info['toss']['decision'],

        'SuperOver': 'Y' if won_by == 'SuperOver' else 'N',

        'WinningTeam': match_info.get('outcome', {}).get('winner', 'NA'),

        'WonBy': won_by,

        'Margin': margin,

        'Method': match_info.get('method', 'NA'),

        'Player_of_Match': match_info.get('player_of_match', ['NA'])[0],

        'Team1Players': ', '.join(extract_team_players(yaml_data['innings'], match_info['teams'][0])),

        'Team2Players': ', '.join(extract_team_players(yaml_data['innings'], match_info['teams'][1])),

        'Umpire1': match_info.get('umpires', ['NA', 'NA'])[0],

        'Umpire2': match_info.get('umpires', ['NA', 'NA'])[1]

    }

    return match_data


season_tracker = {}

match_number_tracker = {}

yaml_dir = '/Users/hemantg/Desktop/ipl (1)'

output_csv_path = '/Users/hemantg/Desktop/matches-data-5may/updated-matches-5may.csv'

all_matches_data = []


for yaml_file in sorted(os.listdir(yaml_dir)):

    if yaml_file.endswith('.yaml'):

        yaml_file_path = os.path.join(yaml_dir, yaml_file)

        match_data = extract_match_data(yaml_file_path, season_tracker, match_number_tracker)

        all_matches_data.append(match_data)



matches_df = pd.DataFrame(all_matches_data)



matches_df['ID'] = matches_df['ID'].astype(int)



matches_df.sort_values(by=['ID'], ascending=True, inplace=True)



matches_df.to_csv(output_csv_path, index=False)

print(f"All match data has been compiled into: {output_csv_path}")

