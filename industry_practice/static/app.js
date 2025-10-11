// 初始化筛选功能
function initFilters() {
    const searchInput = document.getElementById('search-input');
    const papersContainer = document.getElementById('papers-container');
    const emptyState = document.getElementById('empty-state');
    const filterButtons = document.querySelectorAll('.tag[data-filter-type]');
    const resetFilterButton = document.getElementById('reset-filter');
    const displayCountElement = document.getElementById('display-count');
    const dateFromInput = document.getElementById('date-from');
    const dateToInput = document.getElementById('date-to');

    // 存储当前筛选状态 - 改为支持多选
    const filterState = {
        companies: ['all'],
        tags: ['all'],
        search: '',
        dateFrom: '',
        dateTo: ''
    };

    // 筛选按钮点击事件 - 支持多选
    filterButtons.forEach(button => {
        button.addEventListener('click', function () {
            const filterType = this.getAttribute('data-filter-type');
            const filterValue = this.getAttribute('data-filter-value');
            const filterKey = filterType === 'company' ? 'companies' : 'tags';

            // 如果点击的是"全部"选项
            if (filterValue === 'all') {
                // 重置该类型的所有筛选
                filterState[filterKey] = ['all'];
                // 更新按钮样式
                document.querySelectorAll(`.tag[data-filter-type="${filterType}"]`).forEach(btn => {
                    btn.classList.remove('selected', 'bg-blue-100', 'text-blue-800');
                    btn.classList.add('bg-gray-100', 'text-gray-800');
                });
                this.classList.add('selected', 'bg-blue-100', 'text-blue-800');
                this.classList.remove('bg-gray-100', 'text-gray-800');
            } else {
                // 确保"全部"选项不被选中
                if (filterState[filterKey].includes('all')) {
                    filterState[filterKey] = [];
                    const allButton = document.querySelector(`.tag[data-filter-type="${filterType}"][data-filter-value="all"]`);
                    if (allButton) {
                        allButton.classList.remove('selected', 'bg-blue-100', 'text-blue-800');
                        allButton.classList.add('bg-gray-100', 'text-gray-800');
                    }
                }

                // 切换当前选项的选中状态
                const index = filterState[filterKey].indexOf(filterValue);
                if (index === -1) {
                    // 选中当前选项
                    filterState[filterKey].push(filterValue);
                    this.classList.add('selected', 'bg-blue-100', 'text-blue-800');
                    this.classList.remove('bg-gray-100', 'text-gray-800');
                } else {
                    // 取消选中当前选项
                    filterState[filterKey].splice(index, 1);
                    this.classList.remove('selected', 'bg-blue-100', 'text-blue-800');
                    this.classList.add('bg-gray-100', 'text-gray-800');

                    // 如果没有选中任何选项，自动选中"全部"选项
                    if (filterState[filterKey].length === 0) {
                        filterState[filterKey] = ['all'];
                        const allButton = document.querySelector(`.tag[data-filter-type="${filterType}"][data-filter-value="all"]`);
                        if (allButton) {
                            allButton.classList.add('selected', 'bg-blue-100', 'text-blue-800');
                            allButton.classList.remove('bg-gray-100', 'text-gray-800');
                        }
                    }
                }
            }

            // 执行筛选
            applyFilters();
        });
    });

    // 搜索框输入事件
    searchInput.addEventListener('input', function () {
        filterState.search = this.value.toLowerCase();
        applyFilters();
    });

    // 日期范围筛选事件
    dateFromInput.addEventListener('change', function () {
        filterState.dateFrom = this.value;
        applyFilters();
    });

    dateToInput.addEventListener('change', function () {
        filterState.dateTo = this.value;
        applyFilters();
    });

    // 重置筛选按钮点击事件
    resetFilterButton.addEventListener('click', function () {
        // 重置筛选状态
        filterState.companies = ['all'];
        filterState.tags = ['all'];
        filterState.search = '';
        filterState.dateFrom = '';
        filterState.dateTo = '';

        // 重置搜索框和日期输入框
        searchInput.value = '';
        dateFromInput.value = '';
        dateToInput.value = '';

        // 重置按钮样式
        document.querySelectorAll('.tag[data-filter-type]').forEach(btn => {
            btn.classList.remove('selected', 'bg-blue-100', 'text-blue-800');
            btn.classList.add('bg-gray-100', 'text-gray-800');
        });
        document.querySelectorAll('.tag[data-filter-value="all"]').forEach(btn => {
            btn.classList.add('selected', 'bg-blue-100', 'text-blue-800');
            btn.classList.remove('bg-gray-100', 'text-gray-800');
        });

        // 执行筛选
        applyFilters();
    });

    // 应用筛选条件 - 支持多选和日期范围筛选
    function applyFilters() {
        const rows = document.querySelectorAll('.article-row');
        let visibleCount = 0;

        rows.forEach(row => {
            const company = row.getAttribute('data-company');
            const tags = row.getAttribute('data-tags').split(',').map(tag => tag.trim()).filter(tag => tag !== '');
            const title = row.querySelector('a').getAttribute('title').toLowerCase();
            const dateStr = row.querySelector('td:nth-child(5)').textContent.trim();
            const date = new Date(dateStr);

            // 检查公司筛选条件（支持多选）
            const companyMatch = 
                filterState.companies.includes('all') || 
                filterState.companies.includes(company);

            // 检查标签筛选条件（支持多选）
            const tagMatch = 
                filterState.tags.includes('all') || 
                tags.some(tag => filterState.tags.includes(tag));

            // 检查搜索条件
            const searchMatch = 
                filterState.search === '' || 
                title.includes(filterState.search) ||
                company.toLowerCase().includes(filterState.search);

            // 检查日期范围筛选条件
            let dateMatch = true;
            if (filterState.dateFrom) {
                const fromDate = new Date(filterState.dateFrom);
                dateMatch = date >= fromDate;
            }
            if (filterState.dateTo && dateMatch) {
                const toDate = new Date(filterState.dateTo);
                // 确保包含当天
                toDate.setHours(23, 59, 59, 999);
                dateMatch = date <= toDate;
            }

            // 显示或隐藏行
            if (companyMatch && tagMatch && searchMatch && dateMatch) {
                row.style.display = 'table-row';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        // 更新序号
        let currentIndex = 1;
        rows.forEach(row => {
            if (row.style.display !== 'none') {
                row.querySelector('td:nth-child(1)').textContent = currentIndex;
                currentIndex++;
            }
        });

        // 更新显示计数
        displayCountElement.textContent = `显示 ${visibleCount} 篇文章 (共 ${rows.length} 篇)`;

        // 显示或隐藏空状态
        if (visibleCount === 0) {
            papersContainer.style.display = 'none';
            emptyState.classList.remove('hidden');
        } else {
            papersContainer.style.display = 'table-row-group';
            emptyState.classList.add('hidden');
        }
    }

    // 初始加载时应用筛选
    applyFilters();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initFilters);

// 为empty-state中的重置按钮添加事件监听
document.addEventListener('DOMContentLoaded', function () {
    const resetFilterEmpty = document.getElementById('reset-filter-empty');
    if (resetFilterEmpty) {
        resetFilterEmpty.addEventListener('click', function () {
            const resetFilter = document.getElementById('reset-filter');
            if (resetFilter) {
                resetFilter.click();
            }
        });
    }
});