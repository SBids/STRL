import os
import re
from datetime import datetime


output_directory = '../../analysis/filtered_lines'
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
    except IOError as e:
        print(f"An error occurred while reading/writing files: {e}")

def count_lines():
    try:
        # Check if the log file exists
        if os.path.isfile(output_file_path):
            with open(output_file_path, 'r') as log_file:
                data_rec_count = 0
                interest_sent_count = 0
                data_sent_finally = 0
                interest_rec_count = 0

                suppressed_count = 0
                decision_drop_count = 0

                interest_drop_sm =0
                data_drop_sm = 0

                

                # Count lines containing "Multicast data received" and "Analysis History Interest sent finally"
                for line in log_file:
                    if "Multicast data received" in line:
                        data_rec_count += 1
                    elif "Interest sent finally:" in line:
                        interest_sent_count += 1
                    elif "Data sent finally:" in line:
                        data_sent_finally += 1
                    elif "Multicast interest received" in line:
                        interest_rec_count += 1
                    elif "suppressed":
                        suppressed_count += 1
                    elif "decision=drop" in line:
                        decision_drop_count +=1
                    elif "Interest drop by suppression, with name":
                        interest_drop_sm += 1
                    elif "Data drop by suppression, with name":
                        data_drop_sm += 1
                    
                print(f"Count of lines with 'Multicast interest received': {interest_rec_count}")
                print(f"Count of lines with 'Interest sent finally': {interest_sent_count}")
                print(f"Count of lines with 'Multicast data received': {data_rec_count}")
                print(f"Count of lines with 'Data sent finally': {data_sent_finally}")
                print(f"Count of lines with 'Suppressed': {suppressed_count}")
                print(f"Count of lines with 'Decision drop': {decision_drop_count}")
                print(f"Count of lines with 'SM interest drop': {interest_drop_sm}")
                print(f"Count of lines with 'SM data drop': {data_drop_sm}")
                print()


        else:
            print(f"The log file '{log_file_path}' does not exist.")

    except IOError as e:
        print(f"An error occurred while reading the file: {e}")

# Example log file path

for sta_number in range(1, 12):
    log_file_path = f'/tmp/minindn/sta{sta_number}/log/nfd.log'
    output_file_path = f'../../analysis/rfiltered_lines{sta_number}.txt'
    file_path = f'{output_directory}{sta_number}.txt'
    target_phrases = ['Multicast interest received:', 'Multicast data received:','Interest sent finally:', 'Data sent finally:', 'suppressed', 'decision=drop', 'Interest drop by suppression, with name', 'Data drop by suppression, with name', 'For moving average ', 'Got suppression time']

    data_fetch()
    print("Fetched for node ", sta_number)
    count_lines()


for sta_number in range(2, 12):
    print("Node ", sta_number)
    cat_file_path = f'/tmp/minindn/sta{sta_number}/catchunks-sta1.txt.log'
    with open(cat_file_path, "r") as cat_file:
        for line in cat_file:
            if "Time elapsed: " in line:
                print(line)
            elif "Goodput: " in line:
                print(line)
            elif "Timeouts:" in line:
                print(line)
            elif "Retransmitted segments:" in line:
                print(line)
            elif "RTT min/avg/max" in line:
                print(line)