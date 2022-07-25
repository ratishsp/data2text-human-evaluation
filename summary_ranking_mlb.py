import csv
import argparse
import random

def read_file(input_file):
    with open(input_file) as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    return content


def process(gold_filename, template_filename, macro_filename, ent_filename, ed_cc_filename, output_file):
    gold = read_file(gold_filename)
    template = read_file(template_filename)
    macro = read_file(macro_filename)
    ed_cc = read_file(ed_cc_filename)
    ent = read_file(ent_filename)
    data_map = {0: gold, 1: template, 2:ed_cc , 3: ent, 4: macro}
    idxs = [1738, 115, 187, 173, 739,
            1711, 346, 1507, 1656, 1371,
            631, 515, 1240, 434, 1242,
            73, 1190, 1395, 324, 882]  # random.seed(2); idxs = random.sample(range(1743), 20)


    with open(output_file, mode='w', encoding="utf-8") as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        filewriter.writerow(['code', 'sum1', 'system1', 'sum2', 'system2'])
        for id in idxs:
            print("id", id)
            for i in range(5):
                for j in range(i + 1, 5):
                    if random.random() > 0.5:
                        code = []
                        code.append(str(id))
                        code.append(str(i))
                        code.append(str(j))
                        filewriter.writerow(["#".join(code), data_map[i][id], 'sys'+str(i), data_map[j][id], 'sys'+str(j)])
                    else:
                        code = []
                        code.append(str(id))
                        code.append(str(j))
                        code.append(str(i))
                        filewriter.writerow(["#".join(code), data_map[j][id], 'sys'+str(j), data_map[i][id], 'sys'+str(i)])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Human eval for summary ranking for MLB')
    parser.add_argument('-gold', type=str,
                        help='gold output', default=None)
    parser.add_argument('-template', type=str,
                        help='template output', default=None)
    parser.add_argument('-macro', type=str,
                        help='macro output', default=None)
    parser.add_argument('-ent', type=str,
                        help='ent output', default=None)
    parser.add_argument('-ed_cc', type=str,
                        help='ed_cc output', default=None)
    parser.add_argument('-output_file', type=str,
                        help='write output', default=None)
    args = parser.parse_args()
    process(args.gold, args.template, args.macro, args.ent, args.ed_cc, args.output_file)
