# paperBotV2 包初始化文件

# 可以在此处导入常用模块或定义包级别的常量
from .prompts import PRERANK_PROMPT, FINERANK_PROMPT
from .arxiv import process_papers

__all__ = ['PRERANK_PROMPT', 'FINERANK_PROMPT', 'process_papers']