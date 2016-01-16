LENGTH = 32
OUTPUT_FORMAT = 'int'  # change to 'int' to get int outputs

for input in range(LENGTH):

    input = float(input)

    whole_num = 0  # tracks our whole number
    output = 0  # our output 32-bit mask
    count = 0  # our current count

    for _i in range(LENGTH):
        count += input / LENGTH
        if int(count) > whole_num:
            output = output | 1
            whole_num += 1
        output = output << 1

    if OUTPUT_FORMAT == 'hex':
        print(str(int(input)) + ": '" + format(output, 'x').zfill(LENGTH/4) + "',  # " + format(output, 'b').zfill(LENGTH))

    elif OUTPUT_FORMAT == 'int':
        print(str(int(input)) + ": " + format(output, 'd') + ",  # " + format(output, 'b').zfill(LENGTH))
