import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import LSTM, Dense
from keras.callbacks import EarlyStopping
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split


def load_and_preprocess_data(directory, players_list):
    all_data = pd.DataFrame()
    for filename in os.listdir(directory):
        player_name = filename[:-4]
        if player_name in players_list:
            df = pd.read_csv(os.path.join(directory, filename))
            df['date'] = pd.to_datetime(df['date'], format='%d/%m/%y')
            df['Player'] = player_name
            all_data = pd.concat([all_data, df], ignore_index=True)

    scaler = MinMaxScaler(feature_range=(0, 1))
    all_data['fantasy_score'] = all_data.groupby('Player')['fantasy_score'].transform(
        lambda x: scaler.fit_transform(x.values.reshape(-1, 1)).flatten()
    )

    window_size = 5
    all_data.sort_values(['Player', 'date'], inplace=True)
    all_data['avg_last_5'] = all_data.groupby('Player')['fantasy_score'].rolling(
        window=window_size, min_periods=1).mean().reset_index(0, drop=True)
    all_data['max_last_5'] = all_data.groupby('Player')['fantasy_score'].rolling(
        window=window_size, min_periods=1).max().reset_index(0, drop=True)
    all_data['std_last_5'] = all_data.groupby('Player')['fantasy_score'].rolling(
        window=window_size, min_periods=1).std().reset_index(0, drop=True)

    return all_data


def create_sequences(data, sequence_length):
    X, y = [], []
    players = data['Player'].unique()
    for player in players:
        player_data = data[data['Player'] == player]
        scores = player_data['fantasy_score'].values
        for i in range(len(scores) - sequence_length):
            X.append(scores[i:(i + sequence_length)])
            y.append(scores[i + sequence_length])

    return np.array(X), np.array(y)


def prepare_player_sequences(data, sequence_length, player_name):
    player_data = data[data['Player'] == player_name]
    if len(player_data) < sequence_length:
        raise ValueError(
            f"Not enough data to create a sequence for {player_name}. Need at least {sequence_length} games.")
    sequence = player_data.iloc[-sequence_length:]['fantasy_score'].values.reshape(
        1, sequence_length, 1)
    return sequence


players_list = ['Ishan Kishan', 'RG Sharma', 'Naman Dhir', 'SA Yadav', 'Tilak Varma', 'HH Pandya', 'TH David', 'PP Chawla', 'JJ Bumrah', 'N Thushara', 'N Wadhera',
                'SZ Mulani', 'PD Salt', 'SP Narine', 'A Raghuvanshi', 'SS Iyer', 'VR Iyer', 'RK Singh', 'AD Russell', 'Ramandeep Singh', 'MA Starc', 'CV Varun', 'Harshit Rana', 'VG Arora']
directory = '/Users/hemantg/Desktop/fantasy-score-data-6may'

data = load_and_preprocess_data(directory, players_list)
sequence_length = 18
X, y = create_sequences(data, sequence_length)

X_train_val, X_test, y_train_val, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42, shuffle=False)
X_train, X_val, y_train, y_val = train_test_split(
    X_train_val, y_train_val, test_size=0.18, random_state=42, shuffle=False)

X_train = X_train.reshape((X_train.shape[0], X_train.shape[1], 1))
X_val = X_val.reshape((X_val.shape[0], X_val.shape[1], 1))
X_test = X_test.reshape((X_test.shape[0], X_test.shape[1], 1))

model = Sequential([
    LSTM(50, activation='relu', input_shape=(X_train.shape[1], 1)),
    Dense(1)
])
model.compile(optimizer='adam', loss='mean_squared_error')

early_stopping = EarlyStopping(
    monitor='val_loss', patience=10, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    epochs=100,
    batch_size=32,
    validation_split=0.1,
    callbacks=[early_stopping]
)

test_loss = model.evaluate(X_test, y_test)
print('Test Loss:', test_loss)

plt.figure(figsize=(10, 5))
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Training History')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.show()

test_loss = model.evaluate(X_test, y_test)
print('Final Test Loss:', test_loss)

predictions = model.predict(X_test)
plt.figure(figsize=(10, 5))
plt.plot(predictions, label='Predicted Fantasy Scores')
plt.plot(y_test, label='Actual Fantasy Scores')
plt.title('Comparison of Predictions and Actual Scores')
plt.xlabel('Test Sample')
plt.ylabel('Fantasy Score')
plt.legend()
plt.show()

scalers = {player: MinMaxScaler() for player in players_list}
for player in players_list:
    player_scores = data[data['Player'] ==
                         player]['fantasy_score'].values.reshape(-1, 1)
    scalers[player].fit(player_scores)

for player in players_list:
    try:
        player_sequence = prepare_player_sequences(
            data, sequence_length, player)
        predicted_score_normalized = model.predict(player_sequence)
        predicted_score = scalers[player].inverse_transform(
            predicted_score_normalized)
        print(f"Predicted Fantasy Score for {player}: {predicted_score[0][0]}")
    except ValueError as e:
        print(e)
