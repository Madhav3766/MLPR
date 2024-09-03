import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from keras.models import Sequential
from keras.layers import LSTM, Dense
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
import matplotlib.pyplot as plt
import csv
def read_player_roles(file_path):
    player_roles = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            player_roles[row['name']] = row['role']
    return player_roles
def load_and_preprocess_data(directory, players_list, game_id):
    all_data = pd.DataFrame()
    for filename in os.listdir(directory):
        player_name = filename[:-4]          if player_name in players_list:
            df = pd.read_csv(os.path.join(directory, filename))
            df['date'] = pd.to_datetime(df['date'], format='%d/%m/%y')              df['Player'] = player_name
            df['match_id'] = game_id              all_data = pd.concat([all_data, df], ignore_index=True)
    scaler = MinMaxScaler(feature_range=(0, 1))
    all_data['fantasy_score'] = all_data.groupby('Player')['fantasy_score'].transform(
        lambda x: scaler.fit_transform(x.values.reshape(-1, 1)).flatten()
    )
    window_size = 5      all_data.sort_values(['Player', 'date'], inplace=True)      all_data['avg_last_5'] = all_data.groupby('Player')['fantasy_score'].rolling(window=window_size, min_periods=1).mean().reset_index(0, drop=True)
    all_data['max_last_5'] = all_data.groupby('Player')['fantasy_score'].rolling(window=window_size, min_periods=1).max().reset_index(0, drop=True)
    all_data['std_last_5'] = all_data.groupby('Player')['fantasy_score'].rolling(window=window_size, min_periods=1).std().reset_index(0, drop=True)
    return all_data
def get_players_from_id(df, ID):
    row = df.loc[ID]
    team1_players = row['Team1Players']
    team2_players = row['Team2Players']
    if isinstance(team1_players, str):
        team1_players = [player.strip() for player in team1_players.split(',')]
    else:
        team1_players = list(team1_players)
    if isinstance(team2_players, str):
        team2_players = [player.strip() for player in team2_players.split(',')]
    else:
        team2_players = list(team2_players)
    all_players = list(set(team1_players + team2_players))      return all_players
def prepare_player_sequences(data, sequence_length, player_name):
    player_data = data[data['Player'] == player_name]
    X, y = create_sequences(player_data, sequence_length)
    if len(X.shape) >= 2:
        X = X.reshape((X.shape[0], X.shape[1], 1))
    else:
        X = np.empty((0, sequence_length, 1))
    return X
df_teams = pd.read_csv('/Users/hemantg/Desktop/updated-matches-6may.csv')
print(df_teams.index)
if 'ID' not in df_teams.index:
    df_teams.set_index('ID', inplace=True)  game_ids = input("Enter the game IDs separated by spaces: ").split()
directory = '/Users/hemantg/Desktop/fantasy-score-data-6may'
output_dir = input("Enter the path to the output directory: ")
player_roles_file = input("Enter the path to the CSV file containing player roles: ")
cricket_players = read_player_roles(player_roles_file)
for game_id in game_ids:
    try:
        game_id = int(game_id)
        players_list = get_players_from_id(df_teams, game_id)
        data = load_and_preprocess_data(directory, players_list, game_id)
        sequence_length = 18          X, y = create_sequences(data, sequence_length)
        X_train_val, X_test, y_train_val, y_test = train_test_split(X, y, test_size=0.15, random_state=42, shuffle=False)
        X_train, X_val, y_train, y_val = train_test_split(X_train_val, y_train_val, test_size=0.18, random_state=42, shuffle=False)          X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
        X_val = X_val.reshape((X_val.shape[0], X_val.shape[1], 1))
        X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))
        model = Sequential([
            LSTM(50, activation='relu', input_shape=(X_train.shape[1], 1)),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mean_squared_error')
        early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
        history = model.fit(
            X_train, y_train,
            epochs=100,
            batch_size=32,
            validation_split=0.1,              callbacks=[early_stopping]
        )
        test_loss = model.evaluate(X_test, y_test)
        print(f'Test Loss for Game ID {game_id}: {test_loss}')
        plt.figure(figsize=(10, 5))
        plt.plot(history.history['loss'], label='Train Loss')
        plt.plot(history.history['val_loss'], label='Validation Loss')
        plt.title('Model Training History')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        plt.savefig(os.path.join(output_dir, f'{game_id} - Model Training History Graph.png'))
        plt.close()
        test_loss = model.evaluate(X_test, y_test)
        print(f'Final Test Loss for Game ID {game_id}: {test_loss}')
        predictions = model.predict(X_test)
        plt.figure(figsize=(10, 5))
        plt.plot(predictions, label='Predicted Fantasy Scores')
        plt.plot(y_test, label='Actual Fantasy Scores')
        plt.title('Comparison of Predictions and Actual Scores')
        plt.xlabel('Test Sample')
        plt.ylabel('Fantasy Score')
        plt.legend()
        plt.savefig(os.path.join(output_dir, f'{game_id} - Comparison of Predictions and Actual Scores Graph.png'))
        plt.close()
        scalers = {}
        for player in players_list:
            player_scores = data[data['Player'] == player]['fantasy_score'].values.reshape(-1, 1)
            if player_scores.size > 0:
                scaler = MinMaxScaler()
                scaler.fit(player_scores)
                scalers[player] = scaler
            else:
                print(f"No data available for player {player}. Skipping this player.")
                continue
        player_scores = []
        for player in players_list:
            try:
                if player in scalers:
                    player_sequence = prepare_player_sequences(data, sequence_length, player)
                    predicted_score_normalized = model.predict(player_sequence)
                    predicted_score = scalers[player].inverse_transform(predicted_score_normalized)
                    player_scores.append((player, predicted_score[0][0]))
                    print(f"Predicted Fantasy Score for {player}: {predicted_score[0][0]}")
                else:
                    print(f"No scaler available for {player} due to lack of data.")
            except ValueError as e:
                print(e)
        player_scores.sort(key=lambda x: x[1], reverse=True)
        top_players = player_scores[:11]
        top_players_df = pd.DataFrame(top_players, columns=['Player', 'Fantasy Score'])
        top_players_df.to_csv(os.path.join(output_dir, f'{game_id} - Top 11 Players.csv'), index=False)
    except ValueError as e:
        print(f"Error processing Game ID {game_id}: {e}")
    except KeyError:
        print(f"Game ID {game_id} not found in the dataset.")
        player_roles = {}
        for player in players_list:
            if player in cricket_players:
                player_roles[player] = cricket_players[player]
            else:
                print(f"Player {player} not found in the CSV file.")
        top_players = []
        for role in ['WK', 'AR', 'BAT', 'BWL']:
            role_players = [(player, score) for player, score in player_scores if player_roles.get(player) == role]
            if role_players:
                top_player = max(role_players, key=lambda x: x[1])
                top_players.append(top_player)
        remaining_players = [player for player in player_scores if player not in top_players]
        remaining_players.sort(key=lambda x: x[1], reverse=True)
        top_players.extend(remaining_players[:7])
        top_players_df = pd.DataFrame(top_players, columns=['Player', 'Fantasy Score'])
        top_players_df.to_csv(os.path.join(output_dir, f'{game_id} - Top 11 Players.csv'), index=False)
    except ValueError as e:
        print(f"Error processing Game ID {game_id}: {e}")
    except KeyError:
        print(f"Game ID {game_id} not found in the dataset.")