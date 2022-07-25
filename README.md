# This repo contains the scripts for conducting human evaluation for data2text generation

## Summary Ranking
Generate the csv for MLB:
```
python summary_ranking_mlb.py -gold data/mlb/gold.txt \
        -template data/mlb/template.txt \
        -macro data/mlb/macro.txt \
        -ent data/mlb/ent.txt \
        -ed_cc data/mlb/ent.txt \
        -output_file data/outputs/mlb.csv
```
Generate the csv for RotoWire:
```
python summary_ranking_rotowire.py -gold data/rotowire/gold.txt \
        -template data/rotowire/template.txt \
        -macro data/rotowire/macro.txt \
        -hier data/rotowire/hier.txt \
        -ed_cc data/rotowire/ed_cc.txt \
        -output_file data/outputs/rotowire.csv
```

