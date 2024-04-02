import openpyxl
import os
output_excel_path = f'../../analysis/Xlfile/analysisInference.xlsx'
# wb = openpyxl.Workbook()
# sheet = wb.active
# sheet.append(["Node", "Interest Rec", "Interest Sent","Data Rec", "Data Sent", "Time elapsed", "Goodput", "Timeout", "Retransmitted segment", "RTT"])
# Check if the Excel file exists
if os.path.isfile(output_excel_path):
    wb = openpyxl.load_workbook(output_excel_path)
else:
    wb = openpyxl.Workbook()

sheet = wb.active

# Check if the header row is already present; if not, add it
if sheet['A1'].value is None:
    sheet.append(["Node", "Interest Rec", "Interest Sent", "Data Rec", "Data Sent", "Time elapsed", "Goodput", "Timeout", "RTT min", "RTT avg", "Rtt max", "Retransmitted", "Suppressed", "Decision dropped", "Interest drop", "Data drop"])


print("Script running!!!")
total_int_rec = 0
total_int_sen = 0
total_dat_rec = 0
total_dat_sen = 0

total_time_elapsed = 0
total_goodput = 0
total_timeout = 0
total_retransmitted = 0
total_rtt_min = 0
total_rtt_avg = 0
total_rtt_max = 0
total_suppressed = 0
total_decision_drop = 0
total_interest_drop =0
total_data_drop = 0
consumer_count = 0

total_data_tuples = []
for sta_number in range(1, 12):
    data_tuples = []
    
    log_file_path = f'../../analysis/rfiltered_lines{sta_number}.txt'
    
    cat_file_path = f'/tmp/minindn/sta{sta_number}/catchunks-sta1.txt.log'

    with open(log_file_path, "r") as log_file:
        data_rec_count = 0
        interest_sent_count = 0
        data_sent_finally = 0
        interest_rec_count = 0
        suppressed_count = 0
        decision_drop_count = 0
        interest_drop_sm =0
        data_drop_sm = 0
        time_elapsed = ""
        goodput = ""
        timeout = ""
        retransmitted = ""
        rtt = ""
        rtt_min = ""
        rtt_avg = ""
        rtt_max = ""
        for line in log_file:
            if "Multicast data received" in line:
                data_rec_count += 1
            elif "Interest sent finally:" in line:
                interest_sent_count += 1
            elif "Data sent finally:" in line:
                data_sent_finally += 1
            elif "Multicast interest received" in line:
                interest_rec_count += 1
            elif "suppressed" in line:
                suppressed_count += 1
            elif "decision=drop" in line:
                decision_drop_count +=1
            elif "Interest drop by suppression, with name" in line:
                interest_drop_sm += 1
            elif "Data drop by suppression, with name" in line:
                data_drop_sm += 1
    if(sta_number != 1):
        total_int_rec += interest_rec_count
        total_int_sen += interest_sent_count
        total_dat_rec += data_rec_count
        total_dat_sen += data_sent_finally
        total_suppressed += suppressed_count
        total_decision_drop += decision_drop_count
        total_interest_drop += interest_drop_sm
        total_data_drop += data_drop_sm

        consumer_count += 1

    if os.path.isfile(cat_file_path): 
        with open(cat_file_path, "r") as cat_file:
            for line in cat_file:
                print(line)
                if "Time elapsed: " in line:
                    time_elapsed = float(line.split(' ')[2])
                elif "Goodput: " in line:
                    goodput = float(line.split(' ')[1])
                elif "Timeouts:" in line:
                    timeout = float(line.split(' ')[1])
                elif "Retransmitted segments:" in line:
                    retransmitted = float(line.split(' ')[2])
                elif "RTT min/avg/max" in line:
                    rtt = line.split(' ')[3]
                    rtt_min = float(rtt.split('/')[0])
                    rtt_avg = float(rtt.split('/')[1])
                    rtt_max = float(rtt.split('/')[2])
            total_time_elapsed += time_elapsed
            total_goodput += goodput
            total_timeout += timeout
            total_retransmitted += retransmitted
            total_rtt_min += rtt_min
            total_rtt_avg += rtt_avg
            total_rtt_max += rtt_max
           

    data_tuples.append((sta_number, interest_rec_count, interest_sent_count, data_rec_count, data_sent_finally, time_elapsed, goodput, timeout, rtt_min, rtt_avg, rtt_max, retransmitted, suppressed_count, decision_drop_count, interest_drop_sm, data_drop_sm))
    print(data_tuples)
    for data_tuple in data_tuples:
        sheet.append(data_tuple)
    print("appended")
total_data_tuples.append((consumer_count, total_int_rec/(consumer_count), total_int_sen/(consumer_count), total_dat_rec/(consumer_count), total_dat_sen/(consumer_count), total_time_elapsed/(consumer_count), total_goodput/(consumer_count), total_timeout/(consumer_count), total_rtt_min/(consumer_count), total_rtt_avg/(consumer_count), total_rtt_max/(consumer_count), total_retransmitted/(consumer_count), total_suppressed/(consumer_count), total_decision_drop/(consumer_count), total_interest_drop/(consumer_count), total_data_drop/(consumer_count)))

print("Data Tuple aftere average", total_data_tuples)
for data_tuple in total_data_tuples:
    sheet.append(data_tuple) 
sheet.append([])  
wb.save(output_excel_path)
print("Log added for ", sta_number)
print(total_dat_rec, consumer_count)