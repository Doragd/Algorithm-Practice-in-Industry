import re
import time
import json
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

class DOINotFoundException(Exception):
    pass

class InvalidDOIURLException(Exception):
    pass

def load_results(filename='results.json'):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError as e:
        raise e.__class__(f"Error loading '{filename}': {str(e)}")

def save_results(results, filename='results.json'):
    try:
        with open(filename, 'w') as file:
            json.dump(results, file, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error: Failed to save results to {filename}: {e}")

class CachedDOICounter:
    def __init__(self):
        self.cache = {}

    def get_citation(self, doi):
        if doi in self.cache:
            return self.cache[doi]
        url = f'https://api.crossref.org/v1/works/{doi}'
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()['message']
            reference_count = data['is-referenced-by-count']
            self.cache[doi] = reference_count
            return reference_count
        except(requests.exceptions.RequestException, KeyError) as e:
            raise DOINotFoundException(f"Failed to fetch {url}: {str(e)}")

def extract_doi(url):
    pattern = re.compile(r'^https?://doi\.org/([^\s]+)$')
    match = pattern.search(url)
    if not match:
        raise InvalidDOIURLException(f"Invalid DOI URL: {url}")
    return match.group(1)

def fill_citation(paper_item, doi_counter):
    try:
        if paper_item['paper_cite'] in [-1, -2]:
            doi = extract_doi(paper_item['paper_url'])
            paper_cite = doi_counter.get_citation(doi)
            paper_item = paper_item.copy()
            paper_item['paper_cite'] = paper_cite
        return paper_item
    except Exception as e:
        print(f"Error: Failed to fill_citation for {paper_item['paper_url']}: {str(e)}")
        return paper_item

def update_results_parallel(conf, papers):
    doi_counter = CachedDOICounter()
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_paper = {
            executor.submit(fill_citation, paper_item, doi_counter): paper_item
            for paper_item in papers
        }
        updated_papers = []
        for future in tqdm(as_completed(future_to_paper), total=len(future_to_paper), desc=f"Updating {conf} papers"):
            paper_item = future_to_paper[future]
            try:
                data= future.result()
            except Exception as e:
                print(f"Error: Failed to update citation for {paper_item['paper_url']}: {str(e)}")
                data = paper_item
            updated_papers.append(data)
    return {conf: updated_papers}

def fetch_parallel(results, confs):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future_to_conf = {
            executor.submit(update_results_parallel, conf, results[conf]): conf
            for conf in confs if conf in results
        }
        for future in as_completed(future_to_conf):
            conf = future_to_conf[future]
            try:
                data = future.result()
            except Exception as e:
                print(f"Error: Failed to update results for {conf}: {str(e)}")
            else:
                results.update(data)
    return results

def update_results(conf, papers):
    doi_counter = CachedDOICounter()
    updated_papers = []
    for paper_item in tqdm(papers, desc=f"Updating {conf} papers"):
        retries = 3
        while retries > 0:
            try:
                data = fill_citation(paper_item, doi_counter)
                break
            except Exception as e:
                print(f"Error: Failed to update citation for {paper_item['paper_url']}: {str(e)}")
                retries -= 1
                if retries == 0:
                    data = paper_item
                    print(f"Use original data for {paper_item['paper_url']}")
                else:
                    time.sleep(1)
        updated_papers.append(data)
        time.sleep(0.5)  # 增加请求之间的时间间隔
    return {conf: updated_papers}

def fetch(results, confs):
    for conf in confs:
        if conf not in results:
            continue
        try:
            data = update_results(conf, results[conf])
        except Exception as e:
            print(f"Error: Failed to update results for {conf}: {str(e)}")
        else:
            results.update(data)
    return results

def run_all(filename='results.json', confs=None, mode='seq'):
    results = load_results(filename)
    if confs is None:
        confs = list(results.keys())
    if mode == 'seq':
        results = fetch(results, confs)
    else:
        results = fetch_parallel(results, confs)
    save_results(results, filename)

if __name__ == '__main__':
    run_all(mode='parallel')