
import re
import openpyxl

def extract_and_store_values(file_path, output_excel):
    # Create a workbook and select the active sheet
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    # Write headers to the Excel sheet
    sheet.append(["Moving Average", "Name", "Time (ms)", "Suppression Time"])

    # Define the regex pattern to extract values
    regex_pattern = r'For moving average (\d+\.\d+) name (.+) from the time (\d+) millisecondsGot suppression time (\d+)'

    with open(file_path, 'r') as file:
        for line in file:
            match = re.search(regex_pattern, line)
            if match:
                moving_average, name, time_ms, suppression_time = match.groups()
                sheet.append([float(moving_average), name, int(time_ms), int(suppression_time)])

    # Save the workbook to the specified Excel file
    workbook.save(output_excel)

# # Example usage:
# input_file = 'your_input_file.txt'
# output_excel_file = 'output_data.xlsx'
# extract_and_store_values(input_file, output_excel_file)




# import re
# import openpyxl

# def extract_and_store_values(file_path, output_excel):
#     # Create a workbook and select the active sheet
#     workbook = openpyxl.Workbook()
#     sheet = workbook.active

#     # Write headers to the Excel sheet
#     sheet.append(["Moving Average", "Name", "Time (ms)"])

#     # Define the regex pattern to extract values
#     regex_pattern = r'For moving average (\d+\.\d+) name (.+) from the time (\d+) milliseconds'

#     with open(file_path, 'r') as file:
#         for line in file:
#             match = re.search(regex_pattern, line)
#             if match:
#                 moving_average, name, time_ms = match.groups()
#                 sheet.append([float(moving_average), name, int(time_ms)])

#     # Save the workbook to the specified Excel file
#     workbook.save(output_excel)

# Example usage:
input_file = '../../analysis/rfiltered_lines2.txt'
output_excel_file = '../../analysis/Xlfile/analysis1ewma.xlsx'
extract_and_store_values(input_file, output_excel_file)

