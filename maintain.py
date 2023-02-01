import re
import ast
import argparse
import openpyxl

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
        assert len(info) > 0 and info[0].get("公司") and info[0].get("内容") and info[0].get("标签") and info[0].get("时间") and info[0].get("链接")
    except:
        raise Exception("[-] Wrong input!")
    return info

def write_item(wb, item):
    columns = ["公司", "内容", "标签", "时间"]
    values = [item[column] for column in columns]
    ws = wb.active
    ws.append(values)
    ws.cell(row=ws.max_row, column=2).style = 'Hyperlink'
    ws.cell(row=ws.max_row, column=2).hyperlink = item["链接"]
    print("[+] Write item: {}".format(values))

def update_excel(args):
    print("[+] Add new items into excel...")
    wb = openpyxl.load_workbook("source.xlsx")
    info = parse_issue(args.issue)
    for item in info:
        assert item.keys() == {"公司", "内容", "标签", "时间", "链接"}
        write_item(wb, item)
    wb.save("source.xlsx")
    print("[+] Add items Done!")

def update_readme(args):
    print("[+] Add new items into readme...")
    info = parse_issue(args.issue)
    with open("README.md", "r", encoding="utf-8") as f:
        line = f.read()
    index = re.search(r"\|(\s-+\s\|)+", line).span(0)[1]
    newlines = ""
    for item in info:
        newline = "".join("| {} | [{}]({}) | {} | {} |".format(
            item["公司"], item["内容"], item["链接"], item["标签"], item["时间"]))
        newlines += newline + "\n"
    newlines = newlines[:-1]
    line = line[:index] + "\n" + newlines + line[index:]
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(line)
    print("[+] Add items Done!")


def main():
    args = set_args()
    update_excel(args)
    update_readme(args)

if __name__ == "__main__":
    main()
