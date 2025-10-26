import json
import os

# 文件路径设置
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
INPUT_FILE = os.path.join(DATA_DIR, 'results.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'results_updated.json')

def process_papers_data(input_file, output_file):
    """
    处理论文数据：
    1. 将translated字段重命名为abstract_translation
    2. 新增title_translation（空字符串）、relevance_score（0）和reasoning（空字符串）字段
    """
    try:
        # 读取原始数据
        print(f"正在读取文件: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_papers = 0
        
        # 处理每个会议的数据
        for conf_name, papers in data.items():
            print(f"处理会议: {conf_name}, 论文数量: {len(papers)}")
            
            for paper in papers:
                # 如果有translated字段，重命名为abstract_translation
                if 'translated' in paper:
                    paper['abstract_translation'] = paper.pop('translated')
                
                # 删除paper_code字段
                if 'paper_code' in paper:
                    del paper['paper_code']
                
                # 新增字段
                paper['title_translation'] = ''
                paper['relevance_score'] = 0
                paper['reasoning'] = ''
                
                total_papers += 1
        
        # 保存更新后的数据
        print(f"总共处理了 {total_papers} 篇论文")
        print(f"正在保存到文件: {output_file}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"数据处理完成！已保存到 {output_file}")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        raise

def main():
    print("开始处理论文数据...")
    process_papers_data(INPUT_FILE, OUTPUT_FILE)
    print("任务完成！")

if __name__ == "__main__":
    main()