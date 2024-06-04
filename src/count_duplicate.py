# Initialize counts
count_is_1_type = 0
count_is_2_type = 0
count_is_3_type = 0
count_is_4_type = 0
count_is_5_type = 0
count_is_6_type = 0
count_is_7_type = 0
count_is_8_type = 0
count_is_9_type = 0
count_is_10_type = 0
for sta_number in range(2,4):
    print("Node ", sta_number)
    cat_file_path = f'/tmp/minindn/sta{sta_number}/log/nfd.log'
    with open(cat_file_path, "r") as cat_file:
        print("opened")
        for line in cat_file:
            if "The duplciat ecount for setUpdateExpiration /producer" in line:
                if "is 1 type " in line:
                    count_is_1_type += 1
                elif "is 2 type " in line:
                    count_is_2_type += 1
                elif "is 3 type " in line:
                    count_is_3_type += 1
                elif "is 4 type " in line:
                    count_is_4_type += 1
                elif "is 5 type " in line:
                    count_is_5_type += 1
                elif "is 6 type " in line:
                    count_is_6_type += 1
                elif "is 7 type " in line:
                    count_is_7_type += 1
                elif "is 8 type " in line:
                    count_is_8_type += 1
                elif "is 9 type " in line:
                    count_is_9_type += 1
                elif "is 10 type " in line:
                    count_is_10_type += 1
        # Print the counts
        print("Number of lines with 'is 1 type':", count_is_1_type)
        print("Number of lines with 'is 2 type':", count_is_2_type)
        print("Number of lines with 'is 3 type':", count_is_3_type)
        print("Number of lines with 'is 4 type':", count_is_4_type)
        print("Number of lines with 'is 5 type':", count_is_5_type)
        print("Number of lines with 'is 6 type':", count_is_6_type)
        print("Number of lines with 'is 7 type':", count_is_7_type)
        print("Number of lines with 'is 8 type':", count_is_8_type)
        print("Number of lines with 'is 9 type':", count_is_9_type)
        print("Number of lines with 'is 10 type':", count_is_10_type)

          