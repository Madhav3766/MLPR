import pandas as pd
import pulp as pl
import os


def load_data(matches_path, ball_by_ball_path):
    try:
        matches_df = pd.read_csv(matches_path)
        ball_by_ball_df = pd.read_csv(ball_by_ball_path)

        if 'Team1Players' in matches_df.columns and matches_df['Team1Players'].dtype == 'object':
            matches_df['Team1Players'] = matches_df['Team1Players'].apply(
                lambda x: x.split(', ') if isinstance(x, str) else [])
        if 'Team2Players' in matches_df.columns and matches_df['Team2Players'].dtype == 'object':
            matches_df['Team2Players'] = matches_df['Team2Players'].apply(
                lambda x: x.split(', ') if isinstance(x, str) else [])

        return matches_df, ball_by_ball_df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


def preprocess_data(matches_df, ball_by_ball_df):
    matches_df = matches_df.drop_duplicates(subset='ID', keep='first')

    team_corrections = {
        'Delhi Daredevils': 'Delhi Capitals',
        'Delhi Capitals': 'Delhi Capitals',
        'Rising Pune Supergiant': 'Rising Pune Supergiants',
        'Royal Challengers Bangalore': 'Royal Challengers Bengaluru'
    }

    for column in ['Team1', 'Team2', 'TossWinner', 'WinningTeam']:
        matches_df[column] = matches_df[column].replace(team_corrections)

    if 'BattingTeam' in ball_by_ball_df.columns:
        ball_by_ball_df['BattingTeam'] = ball_by_ball_df['BattingTeam'].replace(
            team_corrections)

    if 'Method' in matches_df.columns:
        indices_to_remove = matches_df[(matches_df['Method'].notna()) | (
            matches_df['WinningTeam'].isna())]['ID']
        matches_df = matches_df[~matches_df['ID'].isin(indices_to_remove)]
        ball_by_ball_df = ball_by_ball_df[~ball_by_ball_df['match_id'].isin(
            indices_to_remove)]

    return matches_df, ball_by_ball_df


def calculate_batting_performance(ball_by_ball_df, match_id):

    match_balls = ball_by_ball_df[ball_by_ball_df['match_id'] == match_id]

    batting_performance = match_balls.groupby(['batter']).agg(
        runs_scored=pd.NamedAgg(column='batsman_run', aggfunc='sum'),
        balls_faced=pd.NamedAgg(column='ballnumber', aggfunc='count'),
        fours=pd.NamedAgg(column='batsman_run',
                          aggfunc=lambda x: (x == 4).sum()),
        sixes=pd.NamedAgg(column='batsman_run',
                          aggfunc=lambda x: (x == 6).sum())
    ).reset_index()

    ducks_df = match_balls[(match_balls['batsman_run'] == 0) & (
        match_balls['isWicketDelivery'] == 1)].groupby('batter').size().reset_index(name='ducks')
    batting_performance = batting_performance.merge(
        ducks_df, on='batter', how='left')
    batting_performance['ducks'] = batting_performance['ducks'].fillna(0)

    batting_performance['duck_penalty'] = batting_performance['ducks'].apply(
        lambda x: -2 if x > 0 else 0)

    batting_performance['batting_points'] = (
        batting_performance['runs_scored'] +
        batting_performance['fours'] +
        2 * batting_performance['sixes'] +
        batting_performance['duck_penalty']
    )

    batting_performance['30_run_bonus'] = batting_performance['runs_scored'].apply(
        lambda x: 4 if x >= 30 and x < 50 else 0)
    batting_performance['half_century_bonus'] = batting_performance['runs_scored'].apply(
        lambda x: 8 if x >= 50 and x < 100 else 0)
    batting_performance['century_bonus'] = batting_performance['runs_scored'].apply(
        lambda x: 16 if x >= 100 else 0)

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

    valid_wicket_types = ['caught', 'bowled', 'lbw',
                          'stumped', 'caught and bowled', 'hit wicket']
    wickets_df = match_balls[match_balls['kind'].isin(valid_wicket_types)].groupby(
        'bowler').size().reset_index(name='wickets')

    lbw_bowled_df = match_balls[match_balls['kind'].isin(['lbw', 'bowled'])].groupby(
        'bowler').size().reset_index(name='lbw_bowled')
    lbw_bowled_df['lbw_bowled_bonus'] = lbw_bowled_df['lbw_bowled'] * 8

    legal_deliveries = ~match_balls['extra_type'].isin(['noball', 'wide'])
    balls_bowled_df = match_balls[legal_deliveries].groupby(
        'bowler').size().reset_index(name='balls_bowled')
    runs_conceded_df = match_balls.groupby(
        'bowler')['total_run'].sum().reset_index(name='runs_conceded')

    bowling_performance = pd.merge(
        wickets_df, lbw_bowled_df, on='bowler', how='left')
    bowling_performance = pd.merge(
        bowling_performance, balls_bowled_df, on='bowler', how='left')
    bowling_performance = pd.merge(
        bowling_performance, runs_conceded_df, on='bowler', how='left').fillna(0)

    bowling_performance['wicket_points'] = bowling_performance['wickets'] * 25
    bowling_performance['bonus_points'] = bowling_performance.apply(lambda x: (
        4 if x['wickets'] == 3 else 8 if x['wickets'] == 4 else 16 if x['wickets'] >= 5 else 0) + x['lbw_bowled_bonus'], axis=1)

    bowling_performance['overs_bowled'] = bowling_performance['balls_bowled'] // 6
    bowling_performance['economy_rate'] = bowling_performance['runs_conceded'] / \
        bowling_performance['overs_bowled']

    bowling_performance['economy_rate_points'] = bowling_performance.apply(
        lambda x: economy_rate_points(x['overs_bowled'], x['economy_rate']), axis=1)
    overs_df = match_balls[legal_deliveries].groupby(['bowler', 'overs']).agg(
        total_runs=('total_run', 'sum')).reset_index()
    maiden_overs_df = overs_df[overs_df['total_runs'] == 0].groupby(
        'bowler').size().reset_index(name='maiden_overs')
    bowling_performance = pd.merge(
        bowling_performance, maiden_overs_df, on='bowler', how='left').fillna(0)

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

    catches_df = match_balls[match_balls['kind'] == 'caught'].groupby(
        'fielders_involved').size().reset_index(name='catches')
    catches_df['catch_bonus'] = catches_df['catches'].apply(
        lambda x: 4 if x >= 3 else 0)

    stumpings_df = match_balls[match_balls['kind'] == 'stumped'].groupby(
        'fielders_involved').size().reset_index(name='stumpings')

    run_outs_df = match_balls[match_balls['kind'] == 'run out'].groupby(
        'fielders_involved').size().reset_index(name='run_outs')

    from functools import reduce
    dfs = [catches_df, stumpings_df, run_outs_df]
    fielding_performance = reduce(lambda left, right: pd.merge(
        left, right, on='fielders_involved', how='outer'), dfs).fillna(0)

    fielding_performance['fielding_points'] = (
        8 * fielding_performance['catches'] +
        fielding_performance['catch_bonus'] +
        12 * fielding_performance['stumpings'] +
        12 * fielding_performance['run_outs']
    )
    return fielding_performance


def calculate_player_fantasy_score(player_name, matches_df, ball_by_ball_df):
    player_fantasy_scores = []

    player_matches = matches_df[
        (matches_df['Team1Players'].apply(lambda x: player_name in x)) |
        (matches_df['Team2Players'].apply(lambda x: player_name in x))
    ]

    for _, row in player_matches.iterrows():
        match_id = row['ID']
        match_date = row['Date']

        batting_performance = calculate_batting_performance(
            ball_by_ball_df, match_id)
        bowling_performance = calculate_bowling_performance(
            ball_by_ball_df, match_id)
        fielding_performance = calculate_fielding_performance(
            ball_by_ball_df, match_id)

        batting_performance = batting_performance.rename(
            columns={'batter': 'player'})
        bowling_performance = bowling_performance.rename(
            columns={'bowler': 'player'})
        fielding_performance = fielding_performance.rename(
            columns={'fielders_involved': 'player'})

        player_performance = pd.merge(batting_performance[['player', 'total_batting_points']], bowling_performance[[
                                      'player', 'total_bowling_points']], on='player', how='outer')
        player_performance = pd.merge(player_performance, fielding_performance[[
                                      'player', 'fielding_points']], on='player', how='outer').fillna(0)

        player_total_points = player_performance.loc[player_performance['player'] == player_name, [
            'total_batting_points', 'total_bowling_points', 'fielding_points']].sum().sum()
        player_total_points += 4

        player_fantasy_scores.append(
            (match_id, match_date, player_total_points))

    return player_fantasy_scores


def main():
    matches_path = '/Users/hemantg/Desktop/updated-matches-6may.csv'
    ball_by_ball_path = '/Users/hemantg/Desktop/updated-ball-by-ball-5may.csv'
    output_directory = input(
        "Enter the directory path to store the CSV files: ")

    matches_df, ball_by_ball_df = load_data(matches_path, ball_by_ball_path)

    if matches_df is not None and ball_by_ball_df is not None:
        matches_df, ball_by_ball_df = preprocess_data(
            matches_df, ball_by_ball_df)

        all_players = list(set(sum(matches_df['Team1Players'].tolist(
        ) + matches_df['Team2Players'].tolist(), [])))

        for player_name in all_players:
            player_fantasy_scores = calculate_player_fantasy_score(
                player_name, matches_df, ball_by_ball_df)

            player_csv_path = os.path.join(
                output_directory, f"{player_name}.csv")
            player_fantasy_df = pd.DataFrame(player_fantasy_scores, columns=[
                                             'match_id', 'date', 'fantasy_score'])
            player_fantasy_df.to_csv(player_csv_path, index=False)
            print(
                f"Fantasy scores for {player_name} stored in {player_csv_path}")


if __name__ == '__main__':
    main()
