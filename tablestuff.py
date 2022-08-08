import json
import pandas as pd
import random

random.seed(2)


def box_score_to_html(entry):
    bs = entry["box_score"]
    df = pd.read_json(json.dumps(bs))
    newcols = ["PLAYER_NAME", "TEAM_CITY", "MIN", "PTS", "FGM", "FGA",
               "FG3M", "FG3A", "FTM", "FTA", "REB", "AST", "TO", "STL", "BLK"]
    df = df[newcols]
    # print entry["box_score"]["MIN"]
    df = df.rename(columns={'TO': 'TOV'})
    # print 'df.MIN',df.MIN
    # df = df[df.MIN.dtypes == "object" and df.MIN != 'N/A']
    df = df.loc[pd.to_numeric(df.PTS, errors='coerce').sort_values(ascending=False).index]
    df = df.sort_values("TEAM_CITY", kind="mergesort")
    return df.to_html(index=False)


def line_score_to_html(entry):
    home_line = entry["home_line"]
    newhome = {}
    for k, v in home_line.items():
        newhome[k.split('-')[1]] = v
    vis_line = entry["vis_line"]
    newvis = {}
    for k, v in vis_line.items():
        newvis[k.split('-')[1]] = v
    df = pd.DataFrame.from_dict([newhome, newvis])
    newcols = ["CITY", "NAME", "PTS_QTR1", "PTS_QTR2", "PTS_QTR3", "PTS_QTR4",
               "PTS", "FG_PCT", "FG3_PCT", "FT_PCT", "REB", "AST", "TOV", "WINS", "LOSSES"]
    df = df[newcols]
    df = df.sort_values("NAME")
    return df.to_html(index=False)


def summary_to_html(entry):
    return " ".join(entry["summary"])
