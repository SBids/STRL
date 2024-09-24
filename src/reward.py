import csv
import re
import os

# Define the log file and CSV file paths
  # Replace with your actual CSV file path

# Regular expression to find the evaluation lines
evaluation_regex = r"Evaluation at step (\d+): Average Reward = ([\d.]+)"

# Read the log file and extract steps and rewards
for sta_num in range(1,4):
    evaluations = []
    with open(f'/tmp/minindn/sta{sta_num}/reinforcement-sta{sta_num}.log', 'r') as log_file:
        for line in log_file:
            match = re.search(evaluation_regex, line)
            if match:
                step = int(match.group(1))
                avg_reward = float(match.group(2))
                evaluations.append((step, avg_reward))
    

    # Check if the CSV file already exists
    file_exists = os.path.isfile(f'../reward/evaluation_results_{sta_num}.csv')

    # Write the extracted data to the CSV file
    with open(f'../reward/evaluation_results_{sta_num}.csv', 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        
        # Write the header only if the file does not exist
        if not file_exists:
            writer.writerow(['Step', 'Average Reward'])
        
        # Append the evaluation data
        for step, avg_reward in evaluations:
            writer.writerow([step, avg_reward])

    print(f"Data has been written to {sta_num}")