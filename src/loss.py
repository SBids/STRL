import re
import csv
import os

def extract_total_loss_numbers(text):
    # Regular expression to find lines containing "Total Loss" and extract numbers
    pattern = r"Total Loss.*?(\d+(?:\.\d+)?)"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches

def process_file(input_file, output_csv):
    with open(input_file, 'r') as file:
        text = file.read()
    
    numbers = extract_total_loss_numbers(text)
    
    file_exists = os.path.isfile(output_csv)
    
    with open(output_csv, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header only if the file does not already exist
        if not file_exists:
            writer.writerow(['Total Loss Numbers'])  # Header row
        for number in numbers:
            writer.writerow([number])
    print("Loss written ", output_csv)

if __name__ == "__main__":
    
    for sta_num in range(1, 4):
        input_file = f'/tmp/minindn/sta{sta_num}/reinforcement-sta{sta_num}.log'  # Replace with your input file name
        output_csv = f'../loss_log/total_loss_numbers_{sta_num}.csv'  # Output CSV file
        process_file(input_file, output_csv)


# # Regular expression to match the "Total loss" line
# # Handles both 'nan' and numerical values
# loss_regex = r"Total loss  tf\.Tensor\(\[\[\[(\d*\.\d+|\d+)\]\]\]\], shape=\(1, 1, 1\), dtype=float32\)"

# # Directory for CSV files
# csv_directory = '../loss_log'

# # Ensure the CSV directory exists
# os.makedirs(csv_directory, exist_ok=True)

# # Loop over stations from 1 to 3
# for sta_num in range(1, 4):
#     evaluations = []
#     log_file_path = f'/tmp/minindn/sta{sta_num}/reinforcement-sta{sta_num}.log'
    
#     # Read the log file and extract loss values
#     if os.path.isfile(log_file_path):
#         with open(log_file_path, 'r') as log_file:
#             for line in log_file:
#                 match = re.search(loss_regex, line)
#                 if match:
#                     loss_value = match.group(1)
#                     print("loss", loss_value)
#                     # Convert 'nan' to actual float('nan') and numbers to float
#                     if loss_value == 'nan':
#                         loss_value = float('nan')
#                     else:
#                         loss_value = float(loss_value)
#                     evaluations.append(loss_value)
    
#     # Print the loss values
#     print(f"Loss values for station {sta_num}:")
#     for loss_value in evaluations:
#         print(loss_value)

#     # Define the CSV file path
#     csv_file_path = os.path.join(csv_directory, f'evaluation_results_{sta_num}.csv')

#     # Check if the CSV file already exists
#     file_exists = os.path.isfile(csv_file_path)

#     # Write the extracted data to the CSV file
#     with open(csv_file_path, 'a', newline='') as csv_file:
#         writer = csv.writer(csv_file)
        
#         # Write the header only if the file does not exist
#         if not file_exists:
#             writer.writerow(['Loss'])
        
#         # Append the loss data
#         for loss_value in evaluations:
#             writer.writerow([loss_value])

#     print(f"Loss data for station {sta_num} has been written to {csv_file_path}")