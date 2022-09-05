
import re

def main():
    with open('notes.md', 'r') as notes:
        is_table = False
        header = None
        data = []
        for line in notes:
            if is_table:
                if re.match(r'^(\| -* )*\|$', line):
                    continue
                elif re.match(r'^(\| [\d.]* )*\|$', line):
                    nums = line.strip().split('|')
                    nums = [float(elem.strip()) for elem in nums if len(elem) > 0 ]
                    data.append(nums)
                else:
                    print(header)
                    print(data)
                    data = []
                    header = None
                    is_table = False
            if re.match(r'^(\| \w* )*\|$', line):
                is_table = True # found table header
                header = line.strip().split('|')
                header = [colname.strip() for colname in header if len(colname) > 0]
                                

if __name__ == '__main__':
    main()
