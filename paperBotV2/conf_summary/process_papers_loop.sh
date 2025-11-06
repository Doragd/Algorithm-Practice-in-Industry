#!/bin/bash
# -*- coding: utf-8 -*-
# 循环执行论文处理脚本的bash工具
#
# 这个脚本会无限循环执行以下流程：
# 1. 运行 get_free_abstract.py 获取论文摘要
# 2. 运行 convert_to_md.py 将结果转换为Markdown格式
# 3. 短暂休息后继续下一轮

# 配置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志文件
LOG_FILE="process_loop.log"

# 脚本路径
GET_FREE_ABSTRACT_SCRIPT="./get_free_abstract.py"
CONVERT_TO_MD_SCRIPT="./convert_to_md.py"

# 日志函数
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local level=$1
    local message=$2
    
    # 输出到控制台
    case $level in
        "INFO")
            echo -e "${BLUE}${timestamp} - ${level} - ${message}${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}${timestamp} - ${level} - ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}${timestamp} - ${level} - ${message}${NC}"
            ;;
        *)
            echo -e "${timestamp} - ${level} - ${message}"
            ;;
    esac
    
    # 输出到日志文件
    echo "${timestamp} - ${level} - ${message}" >> "$LOG_FILE"
}

# 检查脚本是否存在
check_scripts_exist() {
    if [ ! -f "$GET_FREE_ABSTRACT_SCRIPT" ]; then
        log "ERROR" "找不到脚本: $GET_FREE_ABSTRACT_SCRIPT"
        return 1
    fi
    if [ ! -f "$CONVERT_TO_MD_SCRIPT" ]; then
        log "ERROR" "找不到脚本: $CONVERT_TO_MD_SCRIPT"
        return 1
    fi
    return 0
}

# 运行单个脚本
run_script() {
    local script_path=$1
    local script_name=$(basename "$script_path")
    
    log "INFO" "开始执行 $script_name"
    
    # 输出分隔线
    echo -e "\n=================================================="
    echo -e "执行 $script_name..."
    echo -e "==================================================\n"
    
    # 直接执行脚本，保持进度条显示
    python3 "$script_path"
    local exit_code=$?
    
    # 检查执行状态
    if [ $exit_code -eq 0 ]; then
        echo -e "\n=================================================="
        echo -e "${GREEN}$script_name 执行完成${NC}"
        echo -e "==================================================\n"
        log "INFO" "$script_name 执行成功"
        return 0
    else
        echo -e "\n=================================================="
        echo -e "${RED}$script_name 执行失败，返回码: $exit_code${NC}"
        echo -e "==================================================\n"
        log "ERROR" "$script_name 执行失败，返回码: $exit_code"
        return 1
    fi
}

# 执行Git拉取操作
git_pull() {
    log "INFO" "开始执行 git pull 拉取变更"
    
    # 输出分隔线
    echo -e "\n=================================================="
    echo -e "执行 git pull..."
    echo -e "==================================================\n"
    
    # 执行git pull
    git pull
    local exit_code=$?
    
    # 检查执行状态
    if [ $exit_code -eq 0 ]; then
        echo -e "\n=================================================="
        echo -e "${GREEN}git pull 执行完成${NC}"
        echo -e "==================================================\n"
        log "INFO" "git pull 执行成功"
        return 0
    else
        echo -e "\n=================================================="
        echo -e "${YELLOW}git pull 执行失败，返回码: $exit_code${NC}"
        echo -e "${YELLOW}可能存在合并冲突，继续尝试...${NC}"
        echo -e "==================================================\n"
        log "WARNING" "git pull 执行失败，返回码: $exit_code，可能存在合并冲突"
        return 1
    fi
}

# 执行Git提交和推送操作
git_commit_push() {
    local iteration=$1
    log "INFO" "开始执行 git commit 和 git push 保存变更"
    
    # 输出分隔线
    echo -e "\n=================================================="
    echo -e "执行 git commit 和 git push..."
    echo -e "==================================================\n"
    
    # 检查是否有变更
    git status --porcelain
    if [ $? -eq 0 ] && [ -n "$(git status --porcelain)" ]; then
        # 添加所有变更
        git add .
        
        # 提交变更
        local datetime=$(date '+%m%d%H%M')
        local commit_message="update new conf summary $datetime"
        git commit -m "$commit_message"
        local commit_exit_code=$?
        
        if [ $commit_exit_code -eq 0 ]; then
            echo -e "${GREEN}git commit 成功${NC}"
            
            # 推送变更
            git push
            local push_exit_code=$?
            
            if [ $push_exit_code -eq 0 ]; then
                echo -e "${GREEN}git push 成功${NC}"
                log "INFO" "git commit 和 git push 执行成功"
                return 0
            else
                echo -e "${RED}git push 失败，返回码: $push_exit_code${NC}"
                log "ERROR" "git push 执行失败，返回码: $push_exit_code"
                return 2
            fi
        else
            echo -e "${RED}git commit 失败，返回码: $commit_exit_code${NC}"
            log "ERROR" "git commit 执行失败，返回码: $commit_exit_code"
            return 1
        fi
    else
        echo -e "${YELLOW}没有检测到需要提交的变更${NC}"
        log "INFO" "没有需要提交的变更"
        return 0
    fi
}

# 主循环函数
main_loop() {
    if ! check_scripts_exist; then
        log "ERROR" "必要的脚本文件不存在，程序退出"
        exit 1
    fi
    
    local iteration=0
    
    log "INFO" "开始循环处理论文"
    log "INFO" "按 Ctrl+C 可以终止程序"
    
    while true; do
        iteration=$((iteration + 1))
        log "INFO" "===== 循环迭代 ${iteration} 开始 ====="
        
        # 0. 首先执行 git pull 拉取变更
        log "INFO" "[$(date '+%Y-%m-%d %H:%M:%S')] 开始拉取最新代码"
        git_pull
        
        # 1. 执行 get_free_abstract.py 获取论文摘要
        log "INFO" "[$(date '+%Y-%m-%d %H:%M:%S')] 开始获取论文摘要"
        if ! run_script "$GET_FREE_ABSTRACT_SCRIPT"; then
            log "WARNING" "获取摘要失败，继续尝试下一轮"
        fi
        
        # 2. 执行 convert_to_md.py 将结果转换为Markdown格式
        log "INFO" "[$(date '+%Y-%m-%d %H:%M:%S')] 开始转换为Markdown格式"
        if ! run_script "$CONVERT_TO_MD_SCRIPT"; then
            log "WARNING" "转换为Markdown失败，继续尝试下一轮"
        fi
        
        # 3. 保存变更，commit，然后push
        log "INFO" "[$(date '+%Y-%m-%d %H:%M:%S')] 开始保存变更"
        git_commit_push $iteration
        
        log "INFO" "===== 循环迭代 ${iteration} 完成 ====="
        
        # 4. 短暂休息一段时间
        # 延迟时间：60-180秒（1-3分钟）
        local sleep_time=$((60 + RANDOM % 61))
        log "INFO" "休息 ${sleep_time} 秒后进行下一轮处理..."
        echo -e "${YELLOW}休息 ${sleep_time} 秒后进行下一轮处理...${NC}"
        sleep $sleep_time
    done
}

# 主程序
if [ "$(basename "$0")" = "process_papers_loop.sh" ]; then
    # 添加信号处理，优雅退出
    trap 'echo -e "\n${YELLOW}收到中断信号，程序退出${NC}"; log "INFO" "收到中断信号，程序退出"; exit 0' INT
    
    main_loop
fi