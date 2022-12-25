import csv
import numpy as np
from statsmodels.stats.multicomp import MultiComparison
from scipy import stats
import argparse


def read_file(file_names, fact_type):
    count_dict = {}
    for filename in file_names:
        with(open(filename, newline='')) as csvfile:
            mturk_reader = csv.DictReader(csvfile)
            for row in mturk_reader:
                system_id = row['Input.field_1_2']
                if fact_type == "Supported":
                    choice_type = int_value('Answer.SupChoice1', row) + int_value('Answer.SupChoice2', row) + int_value(
                        'Answer.SupChoice3', row) + int_value('Answer.SupChoice4', row)
                elif fact_type == "Contradicting":
                    choice_type = int_value('Answer.ConChoice1', row) + int_value('Answer.ConChoice2', row) + int_value(
                        'Answer.ConChoice3', row) + int_value('Answer.ConChoice4', row)
                else:
                    assert False
                choice_type /= 4
                if system_id not in count_dict:
                    count_dict[system_id] = []
                count_dict[system_id].append(choice_type)
    print(count_dict)
    for system_id in count_dict:
        print("system id", system_id, "mean", np.mean(count_dict[system_id]), "length", len(count_dict[system_id]))
    return count_dict


def int_value(key, row):
    try:
        con_choice = int(row[key])
    except ValueError:
        con_choice = 0
    return con_choice


def process(count_dict):
    data = []

    for element1, element2, element3, element4, element5 in zip(count_dict['system1'],
                                                                count_dict['system2'],
                                                                count_dict['system3'],
                                                                count_dict['system4'],
                                                                count_dict['system5']):
        data.append((str('system1'), element1))
        data.append((str('system2'), element2))
        data.append((str('system3'), element3))
        data.append((str('system4'), element4))
        data.append((str('system5'), element5))
    # print("data", data)
    data = np.rec.array(data, dtype=[('system', '|U7'), ('Score', '<f8')])
    f, p = stats.f_oneway(data[data['system'] == 'system1'].Score, data[data['system'] == 'system2'].Score,
                          data[data['system'] == 'system3'].Score, data[data['system'] == 'system4'].Score,
                          data[data['system'] == 'system5'].Score)
    print('One-way ANOVA')
    print('=============')

    print('F value:', f)
    print('P value', p, '\n')

    mc = MultiComparison(data['Score'], data['system'])
    result = mc.tukeyhsd()
    print(result)
    print(mc.groupsunique)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Significance test for fact counting')
    parser.add_argument('-fact_type', type=str,
                        help='type of facts to compute significance test for', default=None)
    parser.add_argument('-file_names', '--file_names', nargs='+',
                        help='input file names', required=True)
    args = parser.parse_args()
    count_dict = read_file(args.file_names, args.fact_type)
    process(count_dict)
