import codecs, json
import pandas as pd
import random
import sys
import numpy as np

HOME = "Home"

AWAY = "Away"

NOVAL = '-'
N_A = "N/A"
random.seed(2)

pd.set_option("display.colheader_justify", "left")
def box_score_to_html(entry, players_in_game):
    bs = entry["box_score"]
    df = pd.read_json(json.dumps(bs))
    newcols = ["PLAYER_NAME", "TEAM_CITY", "MIN", "PTS", "FGM", "FGA",
    "FG3M", "FG3A", "FTM", "FTA", "REB", "AST", "TO", "STL", "BLK"]
    #PLAYER_NAME 	TEAM_CITY 	RUN 	RBI 	POS 	AVG 	WLK 	ERR 	HIT 	HR
    newcols = ["full_name", "team", "r", "rbi", "pos", "avg","bb","e","h","hr"]
    df = df[newcols]
    #sLength = len(df['full_name'])
    #df['new'] = pd.Series(np.random.randn(sLength), index=df.index)
    #print 'entry["home_line"]["team_name"]', entry["home_line"]["team_name"]
    #print 'df["team"]', df['team']
    #df['new'] = "HOME" if df['team'][1] == entry["home_line"]["team_name"] else "AWAY"
    df['side'] = df.apply(lambda row: HOME if row['team'] == entry["home_line"]["team_name"] else AWAY, axis=1)
    #print entry["box_score"]["MIN"]
    #df = df.rename(columns={'TO': 'TOV'})
    #print 'df.MIN',df.MIN
    #df = df[df.MIN.dtypes == "object" and df.MIN != 'N/A']
    mask = df['full_name'].isin(['N/A'])
    df = df[~mask]
    mask = df['full_name'].isin(list(players_in_game))
    df = df[mask]
    mask = df['pos'].isin(['N/A'])
    df = df[~mask]
    df = df.sort_values(by=['side', 'r', 'rbi'], ascending=[False, False, False])
    df.columns = ['PLAYER_NAME', 'TEAM', 'RUN', 'RBI', 'POS', 'AVG', 'WLK', 'ERR', 'HIT', 'HR', 'SIDE']
    return df.to_html(index=False)


def pitching_score_to_html(entry, players_in_game):
    bs = entry["box_score"]
    df = pd.read_json(json.dumps(bs))
    #pitching_attrib = ["bb","er","era","h","hr","l","loss","s", "np","r",
                   #"save","so","sv","w","win", "ip1", "ip2"]
    #PLAYER_NAME 	TEAM_CITY 	RUN 	WLK 	HIT 	HR 	ER 	ERA 	NP 	IP		SO		WIN 	LOS		W		L 	SAV 	SV
    newcols = ["full_name", "team", "p_r", "p_bb", "p_h", "p_hr","p_er","p_era","p_np","p_ip1", "p_ip2", "p_so", "p_w", "p_l", "p_win", "p_loss", "p_save", "p_sv"]
    df = df[newcols]
    set_dash('p_ip2', df)
    set_dash('p_win', df)
    set_dash('p_loss', df)
    set_dash('p_save', df)
    df['side'] = df.apply(lambda row: HOME if row['team'] == entry["home_line"]["team_name"] else AWAY, axis=1)
    #print entry["box_score"]["MIN"]
    #df = df.rename(columns={'TO': 'TOV'})
    #print 'df.MIN',df.MIN
    #df = df[df.MIN.dtypes == "object" and df.MIN != 'N/A']
    mask = df['full_name'].isin(['N/A'])
    df = df[~mask]
    mask = df['full_name'].isin(list(players_in_game))
    df = df[mask]
    mask = df['p_r'].isin(['N/A'])
    df = df[~mask]
    df = df.sort_values(by=['side', 'p_ip1'], ascending=[False, False])
    df.columns = ['PLAYER_NAME', 'TEAM', 'RUN', 'WLK', 'HIT', 'HR', 'ER', 'ERA', 'NP', 'IP1','IP2', 'SO', 'WIN', 'LOS', 'W', 'L', 'SAV', 'SV', 'SIDE']
    return df.to_html(index=False)


def set_dash(key, df):
    df[key] = df.apply(lambda row: '-' if row[key] == N_A else row[key], axis=1)


def get_entities_in_play(inning_play):
    entities_found = set()
    for attrib in ["batter", "pitcher", "fielder_error"]:
        if attrib in inning_play:
            entities_found.add(inning_play[attrib])
    for attrib in ["scorers", "b1", "b2", "b3"]:
        if attrib in inning_play and len(inning_play[attrib]) > 0 and inning_play[attrib][0] != "N/A":
            for baserunner_instance in inning_play[attrib]:
                entities_found.add(baserunner_instance)
    return entities_found


def pbyp_score_to_html(entry, innings, players_in_game):
    plays = entry["play_by_play"]
    items = []
    rows = 0
    for inning in range(1, len(entry['home_line']['innings'])+1):
        for top_bottom in ["top", "bottom"]:
            inning_plays = plays[str(inning)][top_bottom]
            play_index = 0
            for inning_play in inning_plays:
                batter = NOVAL
                pitcher = NOVAL
                baserunners = [NOVAL, NOVAL, NOVAL]
                scorers = NOVAL
                fielder_error = NOVAL
                event = NOVAL
                event2 = NOVAL
                if inning_play["runs"] > 0 or (inning in innings and players_in_game&get_entities_in_play(inning_play)):
                    batter = set_value("batter", inning_play)
                    pitcher = set_value("pitcher", inning_play)
                    for baserunner_index, baserunner_key in enumerate(["b1", "b2", "b3"]):
                        if baserunner_key in inning_play and len(inning_play[baserunner_key])>0 and inning_play[baserunner_key][0] != N_A:
                            baserunners[baserunner_index] = []
                            for baserunner_instance in inning_play[baserunner_key]:
                                baserunners[baserunner_index].append(baserunner_instance)
                            baserunners[baserunner_index] = ", ".join(baserunners[baserunner_index])
                    if "scorers" in inning_play and len(inning_play["scorers"])>0:
                        scorers = []
                        for scorer in inning_play["scorers"]:
                            scorers.append(scorer)
                        scorers = ", ".join(scorers)
                    if 'fielder_error' in inning_play:
                        fielder_error = inning_play['fielder_error']
                    event = set_value("event", inning_play)
                    event2 = set_value("event2", inning_play)
                    runs = set_value("runs", inning_play)
                    rbi = set_value("rbi", inning_play)
                    home_team_runs = set_value("home_team_runs", inning_play)
                    away_team_runs = set_value("away_team_runs", inning_play)
                    items.append(batter)
                    items.append(pitcher)
                    items.extend(baserunners)
                    items.append(scorers)
                    items.append(fielder_error)
                    items.append(event)
                    items.append(event2)
                    items.append(runs)
                    items.append(rbi)
                    items.append(home_team_runs)
                    items.append(away_team_runs)
                    items.append(inning)
                    items.append(top_bottom)
                    '''
                    print "batter", batter
                    print "pitcher", pitcher
                    print "baserunners", baserunners
                    print "scorers", scorers
                    print
                    '''
                    rows += 1
    #print "items", items
    columns = ["BATTER", "PITCHER", "BASE1", "BASE2", "BASE3", "SCORER/S", "FIELDER_ERR", "EVENT", "EVENT2", "RUNS", "RBI", entry["home_line"]["team_name"] + " Runs", entry["vis_line"]["team_name"] + " Runs", "INNING", "top_bottom"]
    df = pd.DataFrame(np.array(items).reshape(rows, len(columns)), columns=columns)
    return df.to_html(index=False)


def set_value(key, inning_play):
    attrib_value = NOVAL
    if key in inning_play:
        attrib_value = inning_play[key]
    return attrib_value


def set_city(key, df):
    df[key] = df.apply(lambda row: 'Chicago' if row[key] == 'Chi Cubs' else row[key], axis=1)
    df[key] = df.apply(lambda row: 'New York' if row[key] == 'NY Yankees' else row[key], axis=1)
    df[key] = df.apply(lambda row: 'Los Angeles' if row[key] == 'LA Dodgers' else row[key], axis=1)
    df[key] = df.apply(lambda row: 'Los Angeles' if row[key] == 'LA Angels' else row[key], axis=1)
    df[key] = df.apply(lambda row: 'New York' if row[key] == 'NY Mets' else row[key], axis=1)
    df[key] = df.apply(lambda row: 'Chicago' if row[key] == 'Chi White Sox' else row[key], axis=1)
    df[key] = df.apply(lambda row: 'Chicago' if row[key] == 'Chi Red Sox' else row[key], axis=1)


def line_score_to_html(entry):
    home_line = entry["home_line"]
    newhome = {}
    for k,v in home_line.items():
        newhome[k] = v
    #print 'newhome', newhome
    vis_line = entry["vis_line"]
    newvis = {}
    for k,v in vis_line.items():
        newvis[k] = v
    df = pd.DataFrame.from_dict([newhome, newvis])
    newcols = ["CITY", "NAME", "PTS_QTR1", "PTS_QTR2", "PTS_QTR3", "PTS_QTR4",
    "PTS", "REB", "AST", "TOV", "WINS", "LOSSES"]
    newcols = ["team_city", "team_name", "team_runs", "team_hits", "team_errors", "result"]
    df = df[newcols]
    df['side'] = df.apply(lambda row: HOME if row['team_name'] == entry["home_line"]["team_name"] else AWAY, axis=1)
    set_city('team_city', df)
    df = df.sort_values(by=['side'], ascending=[False])
    df.columns = ['CITY', 'NAME', 'RUNS', 'HIT', 'ERR', 'RESULT', 'SIDE']
    return df.to_html(index=False)

def summary_to_html(entry):
    return " ".join(entry["summary"])


if __name__ == '__main__':
    #with codecs.open("../../roto_nba_prepdata.json", "r", "utf-8") as f:
    with codecs.open("/home/ratish/project/deepnlp/genfromtable/mlb/dataset/ver13/mlb/json/test.json", "r", "utf-8") as f:
        data = json.load(f)
    print('len(data["test"])',len(data))
    idxs = list(range(len(data)-1))
    random.shuffle(idxs)


    #idxs = idxs[:K]
    idxs = [670, 796, 1070, 1232, 878, 314, 905, 271, 1406, 1559, 1272, 1403, 894, 1365, 251, 428, 325, 74, 1623, 179, 536,
            835, 615, 1428, 583, 568, 1650, 29, 685, 484]

    print("using", idxs)

    # using [256, 126, 390, 418, 407, 717, 87, 666, 534, 447, 577, 172, 394, 259, 643, 204, 606, 654, 55, 538, 682, 528, 580, 347, 5, 655, 306, 468, 552, 45]


    skeletonfi = "inforating-menu.skeleton_mlb.html"
    with open(skeletonfi) as f:
        skeletonlines = f.readlines()


    for i, idx in enumerate(idxs):
        linescore_html = line_score_to_html(data[idx])
        #print
        boxscore_html = box_score_to_html(data[idx])

        pitching_score_html = pitching_score_to_html(data[idx])
        pbyp_score_html = pbyp_score_to_html(data[idx])

        with open("templates_inp_mlb/inforating-menu.skeleton-" + str(i) + ".html", "w+") as f:
            for line in skeletonlines:
                if "Please use the following" in line:
                    f.write(line)
                    f.write("<div> %s </div>\n" % linescore_html)
                    f.write("<br/>")
                    f.write("<div> %s </div>\n" % boxscore_html)
                    f.write("<br/>")
                    f.write("<div> %s </div>\n" % pitching_score_html)
                    f.write("<br/>")
                    f.write("<div> %s </div>\n" % pbyp_score_html)
                    f.write("<br/>")
                    #f.write("<div><b>Summary</b>: %s </div>\n" % summary_to_html(data[idx]).encode("utf-8"))
                    f.write("<br/>")
                else:
                    f.write(line)
