# -*- coding: utf-8 -*-
import json, csv
from nltk import sent_tokenize, word_tokenize
import random
from text2num import text2num, NumberException
import argparse
from tablestuff import line_score_to_html, box_score_to_html

number_words = set(["one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
                    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand"])

DELIM = "|"
HOME = "HOME"
AWAY = "AWAY"


def get_ents(dat):
    players = set()
    teams = set()
    cities = set()
    for thing in dat:
        teams.add(thing["vis_name"])
        teams.add(thing["vis_line"]["TEAM-NAME"])
        teams.add(thing["vis_city"] + " " + thing["vis_name"])
        teams.add(thing["vis_city"] + " " + thing["vis_line"]["TEAM-NAME"])
        teams.add(thing["home_name"])
        teams.add(thing["home_line"]["TEAM-NAME"])
        teams.add(thing["home_city"] + " " + thing["home_name"])
        teams.add(thing["home_city"] + " " + thing["home_line"]["TEAM-NAME"])
        # special case for this
        if thing["vis_city"] == "Los Angeles":
            teams.add("LA" + thing["vis_name"])
        if thing["home_city"] == "Los Angeles":
            teams.add("LA" + thing["home_name"])
        # sometimes team_city is different
        cities.add(thing["home_city"])
        cities.add(thing["vis_city"])
        players.update(list(thing["box_score"]["PLAYER_NAME"].values()))
        cities.update(list(thing["box_score"]["TEAM_CITY"].values()))

    for entset in [players, teams, cities]:
        for k in list(entset):
            pieces = k.split()
            if len(pieces) > 1:
                for piece in pieces:
                    if len(piece) > 1 and piece not in ["II", "III", "Jr.", "Jr"]:
                        entset.add(piece)

    all_ents = players | teams | cities

    return all_ents, players, teams, cities


def extract_entities(sent, all_ents):
    sent_ents = []
    i = 0
    while i < len(sent):
        if sent[i] in all_ents:  # findest longest spans; only works if we put in words...
            j = 1
            while i + j <= len(sent) and " ".join(sent[i:i + j]) in all_ents:
                j += 1
            sent_ents.append((i, i + j - 1, " ".join(sent[i:i + j - 1]), False))
            i += j - 1
        else:
            i += 1
    return sent_ents


def annoying_number_word(sent, i):
    ignores = set(["three point", "three - point", "three - pt", "three pt", "three - pointers", "three - pointer",
                   "three pointers"])
    return " ".join(sent[i:i + 3]) in ignores or " ".join(sent[i:i + 2]) in ignores


def extract_numbers(sent):
    sent_nums = []
    i = 0
    ignores = set(["three point", "three-point", "three-pt", "three pt"])
    # print sent
    while i < len(sent):
        toke = sent[i]
        a_number = False
        try:
            itoke = int(toke)
            a_number = True
        except ValueError:
            pass
        if a_number:
            sent_nums.append((i, i + 1, int(toke)))
            i += 1
        elif toke in number_words and not annoying_number_word(sent, i):  # get longest span  (this is kind of stupid)
            j = 1
            while i + j < len(sent) and sent[i + j] in number_words and not annoying_number_word(sent, i + j):
                j += 1
            try:
                sent_nums.append((i, i + j, text2num(" ".join(sent[i:i + j]))))
            except NumberException:
                pass
                # print sent
                # print sent[i:i+j]
                # assert False
            i += j
        else:
            i += 1
    return sent_nums


def get_player_idx(bs, entname):
    keys = []
    for k, v in bs["PLAYER_NAME"].items():
        if entname == v:
            keys.append(k)
    if len(keys) == 0:
        for k, v in bs["SECOND_NAME"].items():
            if entname == v:
                keys.append(k)
        if len(keys) > 1:  # take the earliest one
            keys.sort(key=lambda x: int(x))
            keys = keys[:1]
            # print "picking", bs["PLAYER_NAME"][keys[0]]
    if len(keys) == 0:
        for k, v in bs["FIRST_NAME"].items():
            if entname == v:
                keys.append(k)
        if len(keys) > 1:  # if we matched on first name and there are a bunch just forget about it
            return None
            # if len(keys) == 0:
            # print "Couldn't find", entname, "in", bs["PLAYER_NAME"].values()
    assert len(keys) <= 1, entname + " : " + str(list(bs["PLAYER_NAME"].values()))
    return keys[0] if len(keys) > 0 else None


def get_rels(entry, ents, nums, players, teams, cities):
    rels = []
    bs = entry["box_score"]
    for i, ent in enumerate(ents):
        if ent[3]:  # pronoun
            continue  # for now
        entname = ent[2]
        if entname in players and entname not in cities and entname not in teams:
            pidx = get_player_idx(bs, entname)
            for j, numtup in enumerate(nums):
                found = False
                strnum = str(numtup[2])
                if pidx is not None:
                    for colname, col in bs.items():
                        if col[pidx] == strnum:
                            rels.append((ent, numtup, "PLAYER-" + colname, pidx))
                            found = True
                if not found:
                    rels.append((ent, numtup, "NONE", None))

        else:  # has to be city or team
            entpieces = entname.split()
            linescore = None
            is_home = None
            if entpieces[0] in entry["home_city"] or entpieces[-1] in entry["home_name"]:
                linescore = entry["home_line"]
                is_home = True
            elif entpieces[0] in entry["vis_city"] or entpieces[-1] in entry["vis_name"]:
                linescore = entry["vis_line"]
                is_home = False
            elif "LA" in entpieces[0]:
                if entry["home_city"] == "Los Angeles":
                    linescore = entry["home_line"]
                    is_home = True
                elif entry["vis_city"] == "Los Angeles":
                    linescore = entry["vis_line"]
                    is_home = False
            for j, numtup in enumerate(nums):
                found = False
                strnum = str(numtup[2])
                if linescore is not None:
                    for colname, val in linescore.items():
                        if val == strnum:
                            rels.append((ent, numtup, colname, is_home))
                            found = True
                if not found:
                    rels.append((ent, numtup, "NONE", None))
    return rels


def read_file(input_file):
    with open(input_file, mode="r", encoding="utf-8") as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    return content


def select_sentences(inp_file, gold_filename, template_filename, macro_filename, hier_filename, ed_cc_filename,
                     output_file):
    with open(inp_file, mode="r", encoding="utf-8") as f:
        trdata = json.load(f)
    all_ents, players, teams, cities = get_ents(trdata)
    hier = read_file(hier_filename)
    gold = read_file(gold_filename)
    template = read_file(template_filename)
    macro = read_file(macro_filename)
    ed_cc = read_file(ed_cc_filename)
    data_map = {0: gold, 1: template, 2: ed_cc, 3: hier, 4: macro}
    idxs = [256, 126, 390, 418, 407,
            717, 87, 666, 534, 447,
            577, 172, 394, 259, 643,
            204, 606, 654, 55, 538]
    with open(output_file, 'w') as csvfile:
        turkwriter = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL, )
        turkwriter.writerow(
            ['list'] + ['html'] + ['item_1_section'] + ['item_1_number'] + ['item_1_condition'] + ['field_1_1'] +
            ['field_1_2'] + ['field_1_3'] +
            ['item_2_section'] + ['item_2_number'] + ['item_2_condition'] + ['field_2_1'] +
            ['item_3_section'] + ['item_3_number'] + ['item_3_condition'] + ['field_3_1'] +
            ['item_4_section'] + ['item_4_number'] + ['item_4_condition'] + ['field_4_1'])
        for serial_no, id in zip(list(range(20)), idxs[:20]):
            print(("serial_no", serial_no, "id", id))
            linescore_html = line_score_to_html(trdata[serial_no]).replace("\n", " ")
            boxscore_html = box_score_to_html(trdata[serial_no]).replace("\n", " ")
            html = "<div> %s </div> <br/> <div> %s </div> <br/> " % (linescore_html, boxscore_html)
            rows = []
            for system in range(5):
                summ = data_map[system][id]
                summ = summ.replace("\u2019", "'")
                sents = sent_tokenize(summ)
                entry = trdata[serial_no]
                selected_sents = []

                for j, sent in enumerate(sents):

                    tokes = word_tokenize(sent)
                    ents = extract_entities(tokes, all_ents)
                    nums = extract_numbers(tokes)
                    # should return a list of (enttup, numtup, rel-name, identifier) for each rel licensed by the table
                    rels = get_rels(entry, ents, nums, players, teams, cities)
                    for (enttup, numtup, label, idthing) in rels:
                        if label != 'NONE':
                            if sent not in selected_sents:
                                selected_sents.append(sent)
                if len(selected_sents) < 4:
                    for i in range(4 - len(selected_sents)):
                        selected_sents.append(sents[random.randint(0, len(sents) - 1)])
                sent_idxs = list(range(len(selected_sents)))
                random.shuffle(sent_idxs)
                sent_idxs = sent_idxs[:4]
                sent_idxs.sort()
                rows.append(
                    ['0', html, 'target', 1, 'check-counts', selected_sents[sent_idxs[0]], 'system' + str(system), id,
                     'target', 2, 'check-counts', selected_sents[sent_idxs[1]],
                     'target', 3, 'check-counts', selected_sents[sent_idxs[2]],
                     'target', 4, 'check-counts', selected_sents[sent_idxs[3]]])
            for row in rows:
                turkwriter.writerow(row)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Select sentences from summary')
    parser.add_argument('-input_path', type=str, default="",
                        help="path to input")
    parser.add_argument('-gold', type=str,
                        help='gold output', default=None)
    parser.add_argument('-template', type=str,
                        help='template output', default=None)
    parser.add_argument('-macro', type=str,
                        help='macro output', default=None)
    parser.add_argument('-hier', type=str,
                        help='hier output', default=None)
    parser.add_argument('-ed_cc', type=str,
                        help='ed_cc output', default=None)
    parser.add_argument('-output_file', type=str,
                        help='write output', default=None)
    args = parser.parse_args()

    select_sentences(args.input_path, args.gold, args.template, args.macro, args.hier, args.ed_cc, args.output_file)
