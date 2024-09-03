import os
import csv
def read_csv(file_path):
    data = {}
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)          for row in reader:
            match_id = row[1].strip()
            player_name = row[0].strip().lower()
            if match_id not in data:
                data[match_id] = []
            data[match_id].append(player_name)
    return data
def calculate_accuracy(csv1_data, csv2_data):
    accuracy_scores = {}
    for match_id in set(csv1_data.keys()) & set(csv2_data.keys()):
        players1 = set(csv1_data[match_id])
        players2 = set(csv2_data[match_id])
        common_players = players1 & players2
        accuracy = len(common_players) / 11
        accuracy_scores[match_id] = accuracy
    return accuracy_scores
reference_file_path = '/Users/hemantg/Desktop/their-algo.csv'
reference_data = read_csv(reference_file_path)
directory_path = '/Users/hemantg/Downloads/combined-pnc-4 wo-fantasy-score'
file_type_average_scores = {}
for filename in os.listdir(directory_path):
    if filename.endswith('.csv'):
        file_path = os.path.join(directory_path, filename)
        csv_data = read_csv(file_path)
        accuracy_scores = calculate_accuracy(reference_data, csv_data)
        file_type = filename.split('-')[0] + ' - ' + filename.split('-')[1]          if file_type not in file_type_average_scores:
            file_type_average_scores[file_type] = []
        file_type_average_scores[file_type].extend(accuracy_scores.values())
output_csv_path = os.path.join(directory_path, 'comparison_average_accuracy_scores.csv')
with open(output_csv_path, 'w', newline='') as output_csv:
    writer = csv.writer(output_csv)
    writer.writerow(['File Type', 'Average Accuracy Score'])
    for file_type, scores in file_type_average_scores.items():
        if scores:
            average_accuracy = sum(scores) / len(scores)
            writer.writerow([file_type, average_accuracy])
        else:
            writer.writerow([file_type, 'No accuracy scores found'])
