import re
import ast
import argparse
import crawler
import citer
import render

FILTERS = ['kddcup', 'w.html', 'lbr.html']

def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", "-i", type=str, help="input issue", required=True)
    args = parser.parse_args()
    return args

def parse_issue(issue):
    try:
        issue = issue.replace("\\n", "").replace("\\r", "")
        info = ast.literal_eval(issue)
        print(info)
        assert isinstance(info, list)
        assert len(info) > 0 and info[0].get("filter") and info[0].get("confs") and info[0].get("year")
    except:
        raise Exception("[-] Wrong input!")
    return info

def run(confs_str, start_year, filter_str='', FILTERS=FILTERS):

    if filter_str:
        FILTERS += filter_str.lower().split(' ')
    
    try:
        confs = confs_str.lower().split(' ')
    except:
        confs = []

    start_year = int(start_year)

    crawler.run_all(
        confs=confs,
        filter_keywords=FILTERS,
        start_year=start_year,
        filename='results.json',
        threads=20
    )

    citer.run_all(
        confs=[conf + str(start_year) for conf in confs],
        mode='parallel'
    )

def main():
    args = set_args()
    info = parse_issue(args.issue)
    assert len(info) == 1 # confs and year
    item = info[0]
    run(
        confs_str=item['confs'], 
        start_year=item['year'],
        filter_str=item['filter'],
    )

if __name__ == "__main__":
    # main()
    run(
        confs_str='cikm',
        start_year=2023,
        filter_str='',
    )




    