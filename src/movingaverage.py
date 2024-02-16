import openpyxl
import os
output_excel_path = f'../../analysis/EWMA/analysisRL.xlsx'

if os.path.isfile(output_excel_path):
    wb = openpyxl.load_workbook(output_excel_path)
else:
    wb = openpyxl.Workbook()

sheet = wb.active

# Check if the header row is already present; if not, add it
if sheet['A1'].value is None:
    sheet.append(["Node", "Moving Average", "Suppression Time", "DC"])


print("Script running!!!")

total_data_tuples = []
for sta_number in range(1, 11):
    data_tuples = []
    
    
    cat_file_path = f'/tmp/minindn/sta{sta_number}/log/nfd.log'


    if os.path.isfile(cat_file_path): 
        with open(cat_file_path, "r") as cat_file:
            for line in cat_file:
                if "Moving average before:" in line:
                    ma = float(line.split(' ')[9])
                    dc = float(line.split(' ')[12])
                    st = float(line.split(' ')[15])   
                    data_tuples.append((sta_number, ma, dc, st))
    for data_tuple in data_tuples:
        sheet.append(data_tuple)


    wb.save(output_excel_path)
    print("Log added for ", sta_number)
    sheet.append([])  

    
