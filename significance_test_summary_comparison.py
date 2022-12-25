import csv
import numpy as np
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.multicomp import MultiComparison
from scipy import stats
import argparse


def read_file(file_names, evaluation_type):
    count_dict = {}
    count_rows = 0
    for filename in file_names:
        with(open(filename, newline='')) as csvfile:
            mturk_reader = csv.DictReader(csvfile)
            for row in mturk_reader:
                input_code = row['Input.code']
                summary_id = input_code.split("#")[0]
                first_system = input_code.split("#")[1]
                second_system = input_code.split("#")[2]
                count_rows += 1
                if summary_id not in count_dict:
                    count_dict[summary_id] = {}
                if first_system not in count_dict[summary_id]:
                    count_dict[summary_id][first_system] = 0
                if second_system not in count_dict[summary_id]:
                    count_dict[summary_id][second_system] = 0
                if row['Answer.' + evaluation_type + "_better"] == "A":
                   count_dict[summary_id][first_system] += 1
                   count_dict[summary_id][second_system] -= 1
                elif row['Answer.' + evaluation_type + "_better"] == "B":
                    count_dict[summary_id][second_system] += 1
                    count_dict[summary_id][first_system] -= 1
                else:
                    pass
                    # assert False
    print(count_dict)
    print("count_rows", count_rows)
    return count_dict


def process(count_dict):
    data = []
    for key in count_dict:
        for system_id in [0, 1, 2, 3]:
            data.append((str(system_id), count_dict[key][str(system_id)]))
    data = np.rec.array(data, dtype= [('system', '|U5'), ('Score', '<i8')])
    f, p = stats.f_oneway(data[data['system'] == '0'].Score,
                          data[data['system'] == '1'].Score, data[data['system'] == '2'].Score,
                          data[data['system'] == '3'].Score)
    print('One-way ANOVA')
    print('=============')

    print('F value:', f)
    print('P value', p, '\n')

    mc = MultiComparison(data['Score'], data['system'])
    result = mc.tukeyhsd()
    print(result)
    print(mc.groupsunique)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Significance test for summary comparison')
    parser.add_argument('-evaluation_type', type=str,
                        help='type of evaluation', default=None)
    parser.add_argument('-file_names', '--file_names', nargs='+',
                        help='input file names', required=True)
    args = parser.parse_args()
    count_dict = read_file(args.file_names, args.evaluation_type)
    process(count_dict)
