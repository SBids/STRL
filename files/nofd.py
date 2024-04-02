import re
import pandas as pd

def extract_numbers(line):
    # Extract numbers after "seg=" and the trailing number
    seg_match = re.search(r'seg=(\d+).*?(\d+)', line)
    seg_number = seg_match.group(1) if seg_match else None
    trailing_number = seg_match.group(2) if seg_match else None

    return seg_number, trailing_number

def process_file(input_file, output_file):
    data = []

    # Read from the input file
    with open(input_file, 'r') as file:
        for line in file:
            seg_number, trailing_number = extract_numbers(line)
            if seg_number and trailing_number:
                data.append({'Seg': int(seg_number), 'Trailing_Number': int(trailing_number)})

    # Create a DataFrame from the extracted data
    df = pd.DataFrame(data)

    # Write to Excel file
    df.to_excel(output_file, index=False)

# Example usage
input_file = '/home/dh127-pc4/workspace/STRL/files/NFD and Nofd/NoFD.txt'
output_file = 'output2.xlsx'
process_file(input_file, output_file)
