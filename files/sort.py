import re

def sort_lines_in_file(filename, regex_pattern):
    with open(filename, 'r') as file:
        lines = file.readlines()

    # Define a function to extract the segment based on the regex pattern
    def extract_segment(line):
        match = re.search(regex_pattern, line)
        return match.group(0) if match else ""

    # Sort the lines based on the extracted segment
    sorted_lines = sorted(lines, key=extract_segment)

    # Write the sorted lines back to the file
    with open(filename, 'w') as file:
        file.writelines(sorted_lines)

# Example usage:
filename = 'NoFD.txt'
regex_pattern = r'/producer/sta1/transfer/v=1708474079916/seg=(\d+)' # Adjust the regex pattern as per your requirement
sort_lines_in_file(filename, regex_pattern)
