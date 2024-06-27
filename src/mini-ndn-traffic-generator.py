

import re
from datetime import datetime
import openpyxl

# log_file_path = '../../filtered_lines13.txt'  # Replace with the actual file path
# output_excel_path = '../../data_fetch_time13.xlsx'  # Replace with the desired output Excel file path

def extract_interest_segment(line):
    match = re.search(r'/producer/sta1/transfer/v=\d+/seg=(\d+)', line)
    if match:
        return match.group(1)
    return None

def find_corresponding_interest(lines, segment, interest_time):
    for line in lines:
        if (float(line.split()[0]) > float(interest_time)):
            if f'Corresponding interest: /producer/sta1/transfer/v=1707102344576/seg={segment}' in line:
                return line.split()[0]
        
    return None

def find_duplicate_count_interest(lines, segment, interest_time):
    for line in lines:
        if (float(line.split()[0]) > float(interest_time)):
            if f'Analysis History Interest: /producer/sta1/transfer/v=1707102344576/seg={segment}' in line:
                # patternI = r'Duplicate count (\d+)type = i'
                patternI = r'(\d+) Analysis History Interest:'
                match = re.search(patternI, line)
                duplicate_count_str = match.group(1)
                return duplicate_count_str

def find_duplicate_count_data(lines, segment, interest_time):
    for line in lines:
        if (float(line.split()[0]) > float(interest_time)):
            if f'Analysis History Data: /producer/sta1/transfer/v=1707102344576/seg={segment}' in line:
                # patternD = r'Duplicate count (\d+)type = d'
                patternD = r'(\d+) Analysis History Data:'
                match = re.search(patternD, line)
                duplicate_count_str = match.group(1)
                return duplicate_count_str

def xl_write():

    try:
        with open(log_file_path, 'r') as log_file:
            lines = log_file.readlines()

            interest_lines = [line for line in lines if 'Interest sent finally' in line]

            data_tuples = []

            for interest_line in interest_lines:

                segment = extract_interest_segment(interest_line)
                interest_time = interest_line.split()[0]
                patternW = r'Wait TIme (\d+) milliseconds'
                match = re.search(patternW, interest_line)
                if match:
                    wait_time_str = match.group(1)
                else:
                    wait_time_str = 0

                if segment:
                    corresponding_interest_line = find_corresponding_interest(lines, segment, interest_time)
                    
                    if corresponding_interest_line:
                        timestamp_interest = float(interest_line.split()[0])
                        timestamp_corresponding_interest = float(corresponding_interest_line.split()[0])
                        time_difference = (timestamp_corresponding_interest - timestamp_interest)*1000
                        dc_interest = find_duplicate_count_interest(lines, segment, interest_time)
                        dc_data = find_duplicate_count_data(lines, segment, interest_time)
                        data_tuples.append((f'/producer/sta1/transfer/v=1707102344576/seg={segment}', timestamp_interest, wait_time_str, timestamp_corresponding_interest, time_difference, dc_interest, dc_data))

            # Create Excel workbook and sheet
            wb = openpyxl.Workbook()
            sheet = wb.active

            # Write data tuples to Excel
            sheet.append(["Segment", "Timestamp Interest", "Interest Suppression time","Timestamp Corresponding Interest", "Time Difference", "Duplicate interest count", "Duplicate data count"])
            for data_tuple in data_tuples:
                sheet.append(data_tuple)

            # Save the Excel file
            wb.save(output_excel_path)
            print(f"Excel with suppression file with data tuples and time differences has been created: {output_excel_path}")

    except IOError as e:
        print(f"An error occurred while reading the log file or writing Excel file: {e}")


for sta_number in range(2, 4):
    log_file_path = f'../../filtered_lines{sta_number}.txt'
    output_excel_path = f'../../data_fetch_time{sta_number}.xlsx'

    xl_write()
    print("Written in xcel for node ", sta_number)





