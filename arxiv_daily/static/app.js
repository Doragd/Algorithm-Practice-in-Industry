/*
 * arXiv每日论文精选前端应用
 * 仅保留可复用的轻量工具函数。
 * 筛选、折叠和日历逻辑由生成页面内的脚本统一负责，避免重复绑定事件。
 */

/**
 * 切换摘要显示状态
 * @param {HTMLElement} button - 按钮元素
 */
function toggleAbstract(button) {
    // 统一使用按钮元素作为参数
    if (!(button instanceof HTMLElement)) return;

    const abstractDiv = button.nextElementSibling;
    if (!abstractDiv) return;

    // 处理不同的显示控制方式
    if (abstractDiv.classList.contains('hidden') || abstractDiv.style.display === 'none') {
        abstractDiv.classList.remove('hidden');
        abstractDiv.style.display = 'block';
        button.textContent = '收起摘要';
    } else {
        abstractDiv.classList.add('hidden');
        abstractDiv.style.display = 'none';
        button.textContent = '查看摘要';
    }
}

/**
 * 设置活跃的筛选器样式
 * @param {string} activeId - 活跃筛选器的ID
 */
function setActiveFilter(activeId) {
    // 重置所有按钮样式
    document.getElementById('show-all').className = 'px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors';
    document.getElementById('show-selected').className = 'px-3 py-1 bg-gray-200 text-gray-700 rounded text-sm hover:bg-gray-300 transition-colors';

    // 设置活跃按钮样式
    document.getElementById(activeId).className = 'px-3 py-1 bg-primary text-white rounded text-sm hover:bg-primary/90 transition-colors';
}
