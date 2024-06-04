import os
import re
from datetime import datetime

# log_file_path = '/tmp/minindn/sta13/log/nfd.log'  # Replace with the actual file path
# output_file_path = '../../rfiltered_lines.txt'  # Replace with the desired output file path
# target_phrases = ['Analysis History Interest /producer/sta1/transfer/v', 'Analysis History Data /producer/sta1/transfer/v','Analysis History Interest sent finally: /producer/sta1/transfer/v', 'Analysis History Satisfied data for Corresponding interest: /producer/sta1/transfer/v']
# # target_phrases = ['Analysis History']

# file_path = '../../filtered_lines13.txt'

def data_fetch():
    try:
        # Check if the log file exists
        if os.path.isfile(log_file_path):
            with open(log_file_path, 'r') as log_file, open(output_file_path, 'w') as output_file:
                lines_to_be_written = [line.strip() for line in log_file if any(phrase in line for phrase in target_phrases)]

                # Write the selected lines to the output file
                if lines_to_be_written:
                    output_file.write('\n'.join(lines_to_be_written))
                    print(f"Filtered lines have been written to '{output_file_path}'")
                else:
                    print("No lines matching the specified target phrases found.")

            
        else:
            print(f"The log file '{log_file_path}' does not exist.")

        with open(output_file_path, 'r') as file:
            lines = file.readlines()

        lines_with_numbers = [(line, int(line.split('=')[-1])) for line in lines]

        # Sort the lines based on the extracted numbers
        sorted_lines = [line for line, _ in sorted(lines_with_numbers, key=lambda x: x[1])]

        # Write the sorted lines back to the text file
        with open(file_path, 'w') as file:
            file.writelines(sorted_lines)  

    except IOError as e:
        print(f"An error occurred while reading/writing files: {e}")

output_directory = '../../filtered_lines'

for sta_number in range(2, 14):
    log_file_path = f'/tmp/minindn/sta{sta_number}/log/nfd.log'
    output_file_path = f'../../rfiltered_lines{sta_number}.txt'
    file_path = f'{output_directory}{sta_number}.txt'
    target_phrases = ['Analysis History Interest: /producer/sta1/transfer/v', 'Analysis History Data: /producer/sta1/transfer/v','Analysis History Interest sent finally: /producer/sta1/transfer/v', 'Analysis History Satisfied data for Corresponding interest: /producer/sta1/transfer/v']

    data_fetch()
    print("Fetched for node ", sta_number)