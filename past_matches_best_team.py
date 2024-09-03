import pandas as pd
import pulp as pl
import ast

def load_data(matches_path, ball_by_ball_path):
    try:
        matches_df = pd.read_csv(matches_path)
        ball_by_ball_df = pd.read_csv(ball_by_ball_path)
    
        if 'Team1Players' in matches_df.columns and matches_df['Team1Players'].dtype == 'object':
            matches_df['Team1Players'] = matches_df['Team1Players'].apply(lambda x: x.split(', ') if isinstance(x, str) else [])
        if 'Team2Players' in matches_df.columns and matches_df['Team2Players'].dtype == 'object':
            matches_df['Team2Players'] = matches_df['Team2Players'].apply(lambda x: x.split(', ') if isinstance(x, str) else [])
        
        return matches_df, ball_by_ball_df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


def preprocess_data(matches_df, ball_by_ball_df):
    team_corrections = {
        'Delhi Daredevils': 'Delhi Capitals',  
        'Delhi Capitals': 'Delhi Capitals',    
        'Rising Pune Supergiant': 'Rising Pune Supergiants',  
        'Royal Challengers Bangalore': 'Royal Challengers Bengaluru'
    }
    for column in ['Team1', 'Team2', 'TossWinner', 'WinningTeam']:
        matches_df[column] = matches_df[column].replace(team_corrections)
    
    if 'BattingTeam' in ball_by_ball_df.columns:
        ball_by_ball_df['BattingTeam'] = ball_by_ball_df['BattingTeam'].replace(team_corrections)

    if 'Method' in matches_df.columns:
        indices_to_remove = matches_df[(matches_df['Method'].notna()) | (matches_df['WinningTeam'].isna())]['ID']
        matches_df = matches_df[~matches_df['ID'].isin(indices_to_remove)]
        ball_by_ball_df = ball_by_ball_df[~ball_by_ball_df['match_id'].isin(indices_to_remove)]
    
    return matches_df, ball_by_ball_df


def calculate_batting_performance(ball_by_ball_df, match_id):
    match_balls = ball_by_ball_df[ball_by_ball_df['match_id'] == match_id] 

    batting_performance = match_balls.groupby(['batter']).agg(
        runs_scored=pd.NamedAgg(column='batsman_run', aggfunc='sum'),
        balls_faced=pd.NamedAgg(column='ballnumber', aggfunc='count'),
        fours=pd.NamedAgg(column='batsman_run', aggfunc=lambda x: (x==4).sum()),
        sixes=pd.NamedAgg(column='batsman_run', aggfunc=lambda x: (x==6).sum())
    ).reset_index()


    ducks_df = match_balls[(match_balls['batsman_run'] == 0) & (match_balls['isWicketDelivery'] == 1)].groupby('batter').size().reset_index(name='ducks')
    batting_performance = batting_performance.merge(ducks_df, on='batter', how='left')
    batting_performance['ducks'] = batting_performance['ducks'].fillna(0)

    batting_performance['duck_penalty'] = batting_performance['ducks'].apply(lambda x: -2 if x > 0 else 0)


    batting_performance['batting_points'] = (
        batting_performance['runs_scored'] +
        batting_performance['fours'] +
        2 * batting_performance['sixes'] +
        batting_performance['duck_penalty']
    )


    batting_performance['30_run_bonus'] = batting_performance['runs_scored'].apply(lambda x: 4 if x >= 30 and x < 50 else 0)
    batting_performance['half_century_bonus'] = batting_performance['runs_scored'].apply(lambda x: 8 if x >= 50 and x < 100 else 0)
    batting_performance['century_bonus'] = batting_performance['runs_scored'].apply(lambda x: 16 if x >= 100 else 0)

    batting_performance['bonus_points'] = batting_performance.apply(
        lambda x: x['century_bonus'] if x['century_bonus'] > 0 else (
            x['half_century_bonus'] if x['half_century_bonus'] > 0 else x['30_run_bonus']),
        axis=1
    )


    def strike_rate_points(runs_scored, balls_faced):
        if balls_faced >= 10:
            strike_rate = (runs_scored / balls_faced) * 100
            if strike_rate >= 170:
                return 6
            elif 150 <= strike_rate < 170:
                return 4
            elif 130 <= strike_rate < 150:
                return 2
            elif strike_rate < 50:
                return -6
            elif 50 <= strike_rate < 60:
                return -4
            elif 60 <= strike_rate < 70:
                return -2
        return 0

    batting_performance['strike_rate_points'] = batting_performance.apply(
        lambda x: strike_rate_points(x['runs_scored'], x['balls_faced']), axis=1
    )

    batting_performance['total_batting_points'] = (
        batting_performance['batting_points'] +
        batting_performance['bonus_points'] +
        batting_performance['strike_rate_points']
    )
    
    return batting_performance


def calculate_bowling_performance(ball_by_ball_df, match_id):
    match_balls = ball_by_ball_df[ball_by_ball_df['match_id'] == match_id]
    
    valid_wicket_types = ['caught', 'bowled', 'lbw', 'stumped', 'caught and bowled', 'hit wicket']
    wickets_df = match_balls[match_balls['kind'].isin(valid_wicket_types)].groupby('bowler').size().reset_index(name='wickets')
    lbw_bowled_df = match_balls[match_balls['kind'].isin(['lbw', 'bowled'])].groupby('bowler').size().reset_index(name='lbw_bowled')
    lbw_bowled_df['lbw_bowled_bonus'] = lbw_bowled_df['lbw_bowled'] * 8
    legal_deliveries = ~match_balls['extra_type'].isin(['noball', 'wide'])
    balls_bowled_df = match_balls[legal_deliveries].groupby('bowler').size().reset_index(name='balls_bowled')
    runs_conceded_df = match_balls.groupby('bowler')['total_run'].sum().reset_index(name='runs_conceded')


    bowling_performance = pd.merge(wickets_df, lbw_bowled_df, on='bowler', how='left')
    bowling_performance = pd.merge(bowling_performance, balls_bowled_df, on='bowler', how='left')
    bowling_performance = pd.merge(bowling_performance, runs_conceded_df, on='bowler', how='left').fillna(0)
    bowling_performance['wicket_points'] = bowling_performance['wickets'] * 25
    bowling_performance['bonus_points'] = bowling_performance.apply(lambda x: (4 if x['wickets'] == 3 else 8 if x['wickets'] == 4 else 16 if x['wickets'] >= 5 else 0) + x['lbw_bowled_bonus'], axis=1)
    bowling_performance['overs_bowled'] = bowling_performance['balls_bowled'] // 6
    bowling_performance['economy_rate'] = bowling_performance['runs_conceded'] / bowling_performance['overs_bowled']

    # economy rate points
    bowling_performance['economy_rate_points'] = bowling_performance.apply(
        lambda x: economy_rate_points(x['overs_bowled'], x['economy_rate']), axis=1)
    overs_df = match_balls[legal_deliveries].groupby(['bowler', 'overs']).agg(total_runs=('total_run', 'sum')).reset_index()
    maiden_overs_df = overs_df[overs_df['total_runs'] == 0].groupby('bowler').size().reset_index(name='maiden_overs')
    bowling_performance = pd.merge(bowling_performance, maiden_overs_df, on='bowler', how='left').fillna(0)
    
    # maiden over points
    bowling_performance['maiden_over_points'] = bowling_performance['maiden_overs'] * 12
    bowling_performance['total_bowling_points'] = (
        bowling_performance['wicket_points'] +
        bowling_performance['bonus_points'] +
        bowling_performance['economy_rate_points'] +
        bowling_performance['maiden_over_points']
    )

    return bowling_performance

def economy_rate_points(overs_bowled, economy_rate):
    if overs_bowled >= 2: 
        if economy_rate < 5:
            return 6
        elif 5 <= economy_rate <= 5.99:
            return 4
        elif 6 <= economy_rate <= 7:
            return 2
        elif 10 <= economy_rate <= 11:
            return -2
        elif 11.01 <= economy_rate <= 12:
            return -4
        elif economy_rate > 12:
            return -6
    return 0


def calculate_fielding_performance(ball_by_ball_df, match_id):
    match_balls = ball_by_ball_df[ball_by_ball_df['match_id'] == match_id]
    
    catches_df = match_balls[match_balls['kind'] == 'caught'].groupby('fielders_involved').size().reset_index(name='catches')
    catches_df['catch_bonus'] = catches_df['catches'].apply(lambda x: 4 if x >= 3 else 0)
    stumpings_df = match_balls[match_balls['kind'] == 'stumped'].groupby('fielders_involved').size().reset_index(name='stumpings')
    run_outs_df = match_balls[match_balls['kind'] == 'run out'].groupby('fielders_involved').size().reset_index(name='run_outs')
    
    from functools import reduce
    dfs = [catches_df, stumpings_df, run_outs_df]
    fielding_performance = reduce(lambda left, right: pd.merge(left, right, on='fielders_involved', how='outer'), dfs).fillna(0)

    fielding_performance['fielding_points'] = (
        8 * fielding_performance['catches'] +  
        fielding_performance['catch_bonus'] +  
        12 * fielding_performance['stumpings'] +  
        12 * fielding_performance['run_outs']  
    )
    
    return fielding_performance




def aggregate_player_points(matches_df, ball_by_ball_df, match_id):
    batting_performance = calculate_batting_performance(ball_by_ball_df, match_id)
    bowling_performance = calculate_bowling_performance(ball_by_ball_df, match_id)
    fielding_performance = calculate_fielding_performance(ball_by_ball_df, match_id)
    batting_performance.rename(columns={'batter': 'player'}, inplace=True)
    bowling_performance.rename(columns={'bowler': 'player'}, inplace=True)
    fielding_performance.rename(columns={'fielders_involved': 'player'}, inplace=True)
    
    total_points = pd.merge(batting_performance[['player', 'total_batting_points']], bowling_performance[['player', 'total_bowling_points']], on='player', how='outer')
    total_points = pd.merge(total_points, fielding_performance[['player', 'fielding_points']], on='player', how='outer').fillna(0)
    
    
    total_points['starting_xi_points'] = 4 

    total_points['total_points'] = (
        total_points['total_batting_points'] + 
        total_points['total_bowling_points'] + 
        total_points['fielding_points'] + 
        total_points['starting_xi_points']
    )
    
    total_points.sort_values(by='total_points', ascending=False, inplace=True)
    return total_points



def add_team_information(total_points_df, matches_df, match_id):
    match_data = matches_df.loc[matches_df['ID'] == match_id].iloc[0]
    team1, team2 = match_data['Team1'], match_data['Team2']
    
    if isinstance(match_data['Team1Players'], str):
        team1_players = match_data['Team1Players'].split(", ")
    else:
        team1_players = match_data['Team1Players']
        
    if isinstance(match_data['Team2Players'], str):
        team2_players = match_data['Team2Players'].split(", ")
    else:
        team2_players = match_data['Team2Players']
    
    player_to_team = {player.strip(): team1 for player in team1_players}
    player_to_team.update({player.strip(): team2 for player in team2_players})
    total_points_df['team'] = total_points_df['player'].map(player_to_team)
    
    return total_points_df


def select_best_dream11_team(total_points_df):
    
    selected_team = total_points_df.nlargest(11, 'total_points')
    selected_team['role'] = 'Player'
    selected_team.loc[selected_team.index[0], 'role'] = 'Captain'
    selected_team.loc[selected_team.index[1], 'role'] = 'Vice Captain'
    selected_team['multiplier'] = 1
    selected_team.loc[selected_team['role'] == 'Captain', 'multiplier'] = 2
    selected_team.loc[selected_team['role'] == 'Vice Captain', 'multiplier'] = 1.5

    selected_team['adjusted_points'] = selected_team['total_points'] * selected_team['multiplier']
    selected_team.reset_index(drop=True, inplace=True)

    total_team_points = selected_team['adjusted_points'].sum()

    final_team = selected_team[['player', 'role', 'total_points', 'adjusted_points']]
    
    print("Final Team: ",final_team)
    print("Total Team Points: ",total_team_points)
    return final_team


def generate_dream11_teams(matches_df, ball_by_ball_df):
    dream11_teams = []

    for match_id in matches_df['ID'].unique():
        total_player_points = aggregate_player_points(matches_df, ball_by_ball_df, match_id)
        total_player_points = add_team_information(total_player_points, matches_df, match_id)
        selected_team = select_best_dream11_team(total_player_points)
        player_points_list = [{'player': row['player'], 'points': row['adjusted_points']} for index, row in selected_team.iterrows()]
        total_team_points = selected_team['adjusted_points'].sum()
        
        dream11_teams.append({
            'match_id': match_id,
            'dream11_team': player_points_list,
            'total_team_points': total_team_points
        })
    
    dream11_teams_df = pd.DataFrame(dream11_teams)
    
    return dream11_teams_df


def generate_all_players_points(matches_df, ball_by_ball_df):
    all_players_teams = []

    for match_id in matches_df['ID'].unique():
        total_player_points = aggregate_player_points(matches_df, ball_by_ball_df, match_id)
        player_points_list = [{'player': row['player'], 'points': row['total_points']} for index, row in total_player_points.iterrows()]
        all_players_teams.append({
            'match_id': match_id,
            'players': player_points_list
        })
    
    all_players_df = pd.DataFrame(all_players_teams)
    
    return all_players_df


def main():
    matches_path = '/Users/madhvendrasingh/Downloads/Work/MLPR/endsem_project/updated-matches-dataset.csv'
    ball_by_ball_path = '/Users/madhvendrasingh/Downloads/Work/MLPR/endsem_project/updated-ball-by-ball-dataset.csv'
    
    matches_df, ball_by_ball_df = load_data(matches_path, ball_by_ball_path)

    if matches_df is not None and ball_by_ball_df is not None:
        matches_df, ball_by_ball_df = preprocess_data(matches_df, ball_by_ball_df)
    
    match_id = matches_df.iloc[-1]['ID']
    total_player_points = aggregate_player_points(matches_df, ball_by_ball_df, match_id)
    total_player_points = add_team_information(total_player_points, matches_df, match_id)
    
    select_best_dream11_team(total_player_points)
     
    # dream11_teams_df = generate_all_players_points(matches_df, ball_by_ball_df)
    # print(dream11_teams_df)
    # dream11_teams_df.to_csv('/Users/madhvendrasingh/Downloads/Work/MLPR/endsem_project/dream11_all_players_streamlit.csv', index=False)
    

if __name__ == '__main__':
    main()

