import json, csv, re
from nltk import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import random
from text2num import text2num, NumberException
from tablestuff_mlb import box_score_to_html, line_score_to_html, pitching_score_to_html, pbyp_score_to_html
import argparse

random.seed(2)

number_words = set(["one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
                    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand"])


def get_ents(thing):
    players = set()
    teams = set()
    cities = set()

    teams.add(thing["vis_name"])
    teams.add(thing["vis_city"] + " " + thing["vis_name"])
    teams.add(thing["home_name"])
    teams.add(thing["home_city"] + " " + thing["home_name"])

    # sometimes team_city is different
    cities.add(thing["home_city"])
    cities.add(thing["vis_city"])
    players.update(list(thing["box_score"]["full_name"].values()))
    players.update(list(thing["box_score"]["last_name"].values()))

    for entset in [players, teams, cities]:
        for k in list(entset):
            pieces = k.split()
            if len(pieces) > 1:
                for piece in pieces:
                    if len(piece) > 1 and piece not in ["II", "III", "Jr.", "Jr"]:
                        entset.add(piece)
                for piece_index in range(1, len(pieces)):
                    entset.add(" ".join(pieces[0: piece_index]))

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


def extract_numbers(sent):
    sent_nums = []
    i = 0
    # print sent
    while i < len(sent):
        toke = sent[i]
        a_number = False
        to_evaluate = toke.replace("/", "")  # handle 1/3
        try:
            itoke = float(to_evaluate)
            a_number = True
        except ValueError:
            pass
        if a_number:
            sent_nums.append((i, i + 1, toke))
            i += 1
        elif toke in number_words:  # and not annoying_number_word(sent, i): # get longest span  (this is kind of stupid)
            j = 1
            while i + j < len(sent) and sent[i + j] in number_words:  # and not annoying_number_word(sent, i+j):
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


# actions such as single, double, homer
def extract_intransitive_actions(sent):
    int_actions = []
    two_word = set(["home run", "home runs", "grounded out", "ground out", "flied out", "sacrifice fly"])
    consider = set(["single", "double", "doubles", "homer", "homers", "scored", "error", "errors", "singled", "doubled",
                    "homered", "singles", "triple", "triples", "tripled", "walk", "walks", "walked", "groundout",
                    "RBI"])
    toke_action_dict = {"single": "single", "double": "double", "doubles": "double", "homer": "home_run",
                        "homers": "home_run", "home run": "home_run", "scored": "scorer", "error": "fielder_error",
                        "errors": "fielder_error", "singled": "single", "doubled": "double", "homered": "home_run",
                        "home runs": "home_run", "singles": "single", "triple": "triple", "triples": "triple",
                        "tripled": "triple", "walk": "walk", "walks": "walk", "walked": "walk",
                        "groundout": "groundout",
                        "grounded out": "groundout", "ground out": "groundout", "flied out": "flyout",
                        "sacrifice fly": "sac_fly", "RBI": "rbi"}
    for i in range(len(sent)):
        toke = sent[i]
        if toke in consider:
            int_actions.append((i, i + 1, toke_action_dict[toke]))
        elif " ".join(sent[i: i + 2]) in two_word:
            int_actions.append((i, i + 2, toke_action_dict[" ".join(sent[i: i + 2])]))
    return int_actions


def get_player_idxs(bs, entname, names_map):
    keys = []
    for k, v in bs["full_name"].items():
        if entname == v:
            keys.append(k)
            names_map[bs["last_name"][k]] = k
    if len(keys) == 0:
        if entname in names_map:
            keys.append(names_map[entname])
    if len(keys) == 0:
        for k, v in bs["last_name"].items():
            if entname == v:
                keys.append(k)
                names_map[entname] = k
    if len(keys) == 0:
        for k, v in bs["first_name"].items():
            if entname == v:
                keys.append(k)
    return keys


def get_player_idx(bs, entname, names_map):
    keys = []
    for k, v in bs["full_name"].items():
        if entname == v:
            keys.append(k)
            names_map[bs["last_name"][k]] = k
    if len(keys) == 0:
        if entname in names_map:
            keys.append(names_map[entname])
    if len(keys) == 0:
        for k, v in bs["last_name"].items():
            if entname == v:
                keys.append(k)
                names_map[entname] = k
        if len(keys) > 1:  # take the earliest one
            keys.sort(key=lambda x: int(x))
            keys = keys[:1]
            names_map[entname] = keys[0]
    if len(keys) == 0:
        for k, v in bs["first_name"].items():
            if entname == v:
                keys.append(k)
        if len(keys) > 1:  # if we matched on first name and there are a bunch just forget about it
            return None
    # assert len(keys) <= 1, entname + " : " + str(bs["full_name"].values())
    return keys[0] if len(keys) > 0 else None


def get_rels(entry, ents, nums, int_actions, players, teams, cities, tokes, innings, names_map):
    rels = []
    bs = entry["box_score"]
    for i, ent in enumerate(ents):
        if ent[3]:  # pronoun
            continue  # for now
        entname = ent[2]
        if entname in players and entname not in cities and entname not in teams:
            pidx = get_player_idx(bs, entname, names_map)
            for j, numtup in enumerate(nums):
                found = False
                strnum = str(numtup[2])
                if pidx is not None:  # player might not actually be in the game or whatever
                    for colname, col in bs.items():
                        if pidx in col and col[pidx] == strnum:  # allow multiple for now
                            if len(tokes) > numtup[1] and tokes[numtup[1]] == "outs" or (
                                        len(tokes) > numtup[1] + 1 and tokes[numtup[1]] == "-" and tokes[
                                    numtup[1] + 1] == "out"):  # ignore two outs or two - out single
                                continue
                            if colname in ["ab", "bb", "hr", "so", "e", "po", "go", "ao", "lob", "d", "r", "cs", "sf",
                                           "sac", "t", "hbp", "fldg", "p_hr", "rbi"]:
                                continue
                            if colname in ["p_bs", "p_sv", "p_hld"] and strnum == "0":
                                continue
                            if len(ents) > i + 1 and ent[0] < ents[i + 1][0] < numtup[
                                0]:  # if there is another entity in between the current entity and num tuple, ignore
                                continue
                            if i > 0 and numtup[0] < ents[i - 1][0] < ent[
                                0]:  # if there is another entity in between the current entity and num tuple
                                # and the order is numtuple ent0 ent1, ignore # check for non pronoun
                                continue
                            if colname == "h" and len(tokes) > numtup[1] and tokes[numtup[1]] != "hits":
                                continue
                            if colname == "sb" and len(tokes) > numtup[1] and tokes[numtup[1]] != "stolen":
                                continue
                            if colname == "a" and len(tokes) > numtup[1] and tokes[numtup[1]] not in ["assists",
                                                                                                      "assist"] and (
                                    len(tokes) <= numtup[1] + 1 or tokes[numtup[1] + 1] not in ["assists", "assist"]):
                                continue
                            rels.append((ent, numtup, "PLAYER-" + colname, pidx))
                            found = True
                    if innings:
                        for colname in ["runs"]:
                            for inning in innings:
                                plays = entry["play_by_play"]
                                if str(inning[0]) not in plays:
                                    continue
                                for top_bottom in ["top", "bottom"]:
                                    inning_plays = plays[str(inning[0])][top_bottom]
                                    for inning_play in inning_plays:
                                        if colname == "runs" and colname in inning_play and str(inning_play[
                                                                                                    colname]) == strnum and len(
                                            tokes) > numtup[1] + 1 and tokes[
                                            numtup[1]] == "-" and tokes[
                                                    numtup[1] + 1] == "run":
                                            if "batter" in inning_play and inning_play[
                                                "batter"] == bs["full_name"][pidx]:
                                                rels.append((ent, numtup, "P-BY-P-" + colname, pidx))
                                                found = True
                                            elif "pitcher" in inning_play and inning_play[
                                                "pitcher"] == bs["full_name"][pidx]:
                                                rels.append((ent, numtup, "P-BY-P-" + colname + "_pitcher", pidx))
                                                found = True
                if not found:
                    rels.append((ent, numtup, "NONE", None))
            for j, inttup in enumerate(int_actions):
                found = False
                if pidx is not None:
                    if inttup[2] in ["single", "double", "triple", "home_run", "scorer", "fielder_error", "walk",
                                     "groundout", "flyout", "sac_fly", "rbi"]:
                        found = check_batter_fielder_in_inning(ent, bs["full_name"][pidx], entry, innings, inttup, pidx,
                                                               rels)
                        if not found:
                            found = check_pitcher_in_inning(ent, bs["full_name"][pidx], entry, innings, inttup, pidx,
                                                            rels)
                if not found and innings:
                    rels.append((ent, inttup, "NONE", None))
        else:  # has to be city or team
            entpieces = entname.split()
            linescore = None
            is_home = None
            if entpieces[-1] == "Sox" and " ".join(entpieces[-2:]) in entry["home_name"]:
                linescore = entry["home_line"]
                is_home = True
            elif entpieces[-1] == "Sox" and " ".join(entpieces[-2:]) in entry["vis_name"]:
                linescore = entry["vis_line"]
                is_home = False
            elif entpieces[0] in entry["home_city"] or entpieces[-1] in entry["home_name"]:
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
                        if colname == "team_errors" and "errors" not in tokes:
                            continue
                        if str(val) == strnum:
                            rels.append((ent, numtup, colname, is_home))
                            found = True
                if not found:
                    rels.append((ent, numtup, "NONE", None))  # should i specialize the NONE labels too?
    rels.sort(key=lambda rel: rel[1][0])
    return rels


def check_pitcher_in_inning(ent, entname, entry, innings, inttup, pidx, rels):
    found = False
    if innings:
        plays = entry["play_by_play"]
        for inning in innings:
            if str(inning[0]) not in plays:
                continue
            for top_bottom in ["top", "bottom"]:
                inning_plays = plays[str(inning[0])][top_bottom]
                for inning_play in inning_plays:
                    if "pitcher" in inning_play and inning_play["pitcher"] == entname:
                        for event_candidate in ["single", "double", "triple", "home_run", "walk", "intent_walk",
                                                "groundout", "flyout", "sac_fly", "rbi"]:
                            if inning_play["event"].lower().replace(" ", "_") == event_candidate and inttup[
                                2] == event_candidate:
                                rels.append((ent, inttup, "P-BY-P-" + inttup[2] + "_pitcher", pidx))
                                found = True
                                return found
                            elif event_candidate == "intent_walk" and inning_play["event"].lower().replace(" ",
                                                                                                           "_") == event_candidate and \
                                            inttup[
                                                2] == "walk":
                                rels.append((ent, inttup, "P-BY-P-" + inttup[2] + "_pitcher", pidx))
                                found = True
                                return found
                            elif event_candidate == "rbi" and inttup[
                                2] == event_candidate and "rbi" in inning_play and int(inning_play["rbi"]) > 0:
                                rels.append((ent, inttup, "P-BY-P-" + inttup[2] + "_pitcher", pidx))
                                found = True
                                return found

    return found


def check_batter_fielder_in_inning(ent, entname, entry, innings, inttup, pidx, rels):
    found = False
    if innings:
        plays = entry["play_by_play"]
        scorers_attrib = "scorers"
        for inning in innings:
            if str(inning[0]) not in plays:
                continue
            for top_bottom in ["top", "bottom"]:
                inning_plays = plays[str(inning[0])][top_bottom]
                for inning_play in inning_plays:
                    if "batter" in inning_play and inning_play["batter"] == entname:
                        for event_candidate in ["single", "double", "triple", "home_run", "walk", "intent_walk",
                                                "groundout", "flyout", "sac_fly", "rbi"]:
                            if inning_play["event"].lower().replace(" ", "_") == event_candidate and inttup[
                                2] == event_candidate:
                                rels.append((ent, inttup, "P-BY-P-" + inttup[2], pidx))
                                found = True
                                return found
                            elif event_candidate == "intent_walk" and inning_play["event"].lower().replace(" ",
                                                                                                           "_") == event_candidate and \
                                            inttup[
                                                2] == "walk":
                                rels.append((ent, inttup, "P-BY-P-" + inttup[2], pidx))
                                found = True
                                return found
                            elif event_candidate == "rbi" and inttup[
                                2] == event_candidate and "rbi" in inning_play and int(inning_play["rbi"]) > 0:
                                rels.append((ent, inttup, "P-BY-P-" + inttup[2], pidx))
                                found = True
                                return found
                    elif "fielder_error" in inning_play and inning_play["fielder_error"] == entname and \
                                    inttup[2] == "fielder_error":
                        rels.append((ent, inttup, "P-BY-P-" + inttup[2], pidx))
                        found = True
                        return found
                    elif scorers_attrib in inning_play and len(inning_play[scorers_attrib]) > 0 and \
                                    inning_play[scorers_attrib][0] != "N/A" and entname in inning_play[
                        scorers_attrib] and \
                                    inttup[2] == "scorer":
                        rels.append((ent, inttup, "P-BY-P-" + inttup[2], pidx))
                        found = True
                        return found
    return found


def read_file(input_file):
    with open(input_file, mode="r", encoding="utf-8") as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    return content


def get_ordinal_adjective_map(ordinal_inning_map_file):
    ordinal_adjective_map_file = open(ordinal_inning_map_file, mode="r", encoding="utf-8")
    ordinal_adjective_map_lines = ordinal_adjective_map_file.readlines()
    ordinal_adjective_map_lines = [line.strip() for line in ordinal_adjective_map_lines]
    ordinal_adjective_map = {}
    for line in ordinal_adjective_map_lines:
        ordinal_adjective_map[line.split("\t")[0]] = line.split("\t")[1]
        key = line.split("\t")[0]
        sents = sent_tokenize(key)
        if len(sents) > 2:
            ordinal_adjective_map[" ".join(sents[-2:])] = line.split("\t")[1]
    return ordinal_adjective_map


def get_inning(sent, prev_sent_context, ordinal_adjective_map):
    inning_identifier = {"first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
                         "7th", "8th", "9th", "10th", "11th", "12th", "13th", "14th", "15th"}
    inning_identifier_map = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
                             "eighth": 8, "ninth": 9, "tenth": 10, "7th": 7, "8th": 8, "9th": 9, "10th": 10, "11th": 11,
                             "12th": 12, "13th": 13, "14th": 14, "15th": 15}
    additional_check = {"16th", "17th", "18th", "19th", "20th", "21st", "22nd", "23rd", "24th", "25th", "26th", "27th",
                        "28th", "29th", "30th"}
    stops = stopwords.words('english')
    innings = []
    upd_sent = " ".join(sent)
    upd_sent = upd_sent.replace("-", " ").split()
    intersected = set(upd_sent).intersection(inning_identifier)
    if len(intersected) > 0:
        # candidate present
        for i in range(len(sent)):
            if sent[i] in inning_identifier and i + 1 < len(sent) and sent[i + 1] in ["inning", "innings"]:
                innings.append((inning_identifier_map[sent[i]], i))
            elif "-" in sent[i] and sent[i].split("-")[0] in inning_identifier and sent[i].split("-")[1] == "inning":
                innings.append((inning_identifier_map[sent[i].split("-")[0]], i))
            elif sent[i] in inning_identifier and i + 2 < len(sent) and sent[i + 1] == "-" and sent[i + 2] == "inning":
                innings.append((inning_identifier_map[sent[i]], i))
            elif (" ".join(sent[:i]).endswith("in the") or " ".join(sent[:i]).endswith("in the top of the") or " ".join(
                    sent[:i]).endswith("in the bottom of the")) and sent[i] in inning_identifier and (
                        (i + 1 < len(sent) and (sent[i + 1] in [".", ","] or sent[i + 1] in stops)) or i + 1 == len(
                        sent)):
                innings.append((inning_identifier_map[sent[i]], i))
            elif sent[i] in inning_identifier and (
                (i + 1 < len(sent) and (sent[i + 1] in [".", ","] or sent[i + 1] in stops)) or i + 1 == len(sent)):
                # i+1 == len(sent) handles the case such as "Kapler also doubled in a run in the first "; no full stop at the end
                expanded_context = prev_sent_context + sent[:i + 1]
                expanded_context = " ".join(expanded_context)
                assert expanded_context in ordinal_adjective_map
                if ordinal_adjective_map[expanded_context] == "True":
                    innings.append((inning_identifier_map[sent[i]], i))
    return innings


def select_sentences(inp_file, gold_filename, template_filename, macro_filename, ent_filename, ed_cc_filename,
                     output_file):
    with open(inp_file, mode="r", encoding="utf-8") as f:
        trdata = json.load(f)
    ent = read_file(ent_filename)
    gold = read_file(gold_filename)
    template = read_file(template_filename)
    macro = read_file(macro_filename)
    ed_cc = read_file(ed_cc_filename)
    data_map = {0: gold, 1: template, 2: ed_cc, 3: ent, 4: macro}

    inning_files = {0: "data/innings/gold_innings",
                    1: "data/innings/template_innings",
                    2: "data/innings/ed_cc_innings",
                    3: "data/innings/ent_innings",
                    4: "data/innings/macro_innings"
                    }
    ordinal_adjective_maps = {}
    for key in inning_files:
        ordinal_adjective_maps[key] = get_ordinal_adjective_map(inning_files[key])

    idxs = [1738, 115, 187, 173, 739,
            1711, 346, 1507, 1656, 1371,
            631, 515, 1240, 434, 1242,
            73, 1190, 1395, 324, 882]
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
            all_ents, players, teams, cities = get_ents(trdata[serial_no])
            rows = []
            entry = trdata[serial_no]
            bs = entry["box_score"]
            players_in_game = set()
            for system in range(5):
                summ = data_map[system][id]
                summ = summ.replace("\u2019", "'")
                sents = sent_tokenize(summ)
                names_map = {}
                for j, sent in enumerate(sents):
                    tokes = word_tokenize(sent)
                    ents = extract_entities(tokes, all_ents)
                    for i, ent in enumerate(ents):
                        entname = ent[2]
                        if entname in players and entname not in cities and entname not in teams:
                            pidxs = get_player_idxs(bs, entname, names_map)
                            for pidx in pidxs:
                                players_in_game.add(bs["full_name"][str(pidx)])
                                # print("players_in_game", players_in_game)
            for system in range(5):
                summ = data_map[system][id]
                summ = summ.replace("\u2019", "'")
                sents = sent_tokenize(summ)
                selected_sents = []
                line_score_html = line_score_to_html(trdata[serial_no]).replace("\n", " ")
                box_score_html = box_score_to_html(trdata[serial_no], players_in_game).replace("\n", " ")
                pitching_score_html = pitching_score_to_html(trdata[serial_no], players_in_game).replace("\n", " ")

                names_map = {}
                sent_inning_map = {}
                for j, sent in enumerate(sents):
                    prev_segment = [] if j == 0 else sents[j - 1].split()
                    innings = get_inning(sent.split(), prev_segment, ordinal_adjective_maps[system])
                    tokes = word_tokenize(sent)
                    ents = extract_entities(tokes, all_ents)
                    nums = extract_numbers(tokes)
                    int_actions = extract_intransitive_actions(tokes)
                    rels = get_rels(entry, ents, nums, int_actions, players, teams, cities, tokes, innings, names_map)
                    for (enttup, numtup, label, idthing) in rels:
                        if label != 'NONE':
                            if sent not in selected_sents:
                                selected_sents.append(sent)
                                sent_inning_map[sent] = [inn[0] for inn in innings]
                if len(selected_sents) < 4:
                    # print("adding", system, len(selected_sents))
                    for i in range(4 - len(selected_sents)):
                        random_sent = sents[random.randint(0, len(sents) - 1)]
                        selected_sents.append(random_sent)
                        if random_sent not in sent_inning_map:
                            sent_inning_map[random_sent] = []
                sent_idxs = list(range(len(selected_sents)))
                selected_innings = [sent_inning_map[selected_sents[sent_idx]] for sent_idx in sent_idxs]
                selected_innings = [item for sublist in selected_innings for item in sublist]
                selected_innings = set(selected_innings)
                pbyp_score_html = pbyp_score_to_html(trdata[serial_no], selected_innings, players_in_game).replace("\n",
                                                                                                                   " ")
                section_html_template = "<div> %s </div> %s </div> <br/>"
                html = " ".join([section_html_template % html_snippet for html_snippet in
                                 zip(["Line score", "Batting", "Pitching", "Play-by-play"],
                                     [line_score_html, box_score_html, pitching_score_html, pbyp_score_html])])
                random.shuffle(sent_idxs)
                sent_idxs = sent_idxs[:4]
                sent_idxs.sort()
                rows.append(
                    [id, html, 'target', 1, 'check-counts', selected_sents[sent_idxs[0]], 'system' + str(system), id,
                     'target', 2, 'check-counts', selected_sents[sent_idxs[1]],
                     'target', 3, 'check-counts', selected_sents[sent_idxs[2]],
                     'target', 4, 'check-counts', selected_sents[sent_idxs[3]]])
            random.shuffle(rows)
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
    parser.add_argument('-ent', type=str,
                        help='ent output', default=None)
    parser.add_argument('-ed_cc', type=str,
                        help='ed_cc output', default=None)
    parser.add_argument('-output_file', type=str,
                        help='write output', default=None)
    args = parser.parse_args()

    select_sentences(args.input_path, args.gold, args.template, args.macro, args.ent, args.ed_cc, args.output_file)
