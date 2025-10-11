// 初始化筛选功能
function initFilters() {
    const searchInput = document.getElementById('search-input');
    const papersContainer = document.getElementById('papers-container');
    const emptyState = document.getElementById('empty-state');
    const filterButtons = document.querySelectorAll('.tag[data-filter-type]');
    const resetFilterButton = document.getElementById('reset-filter');
    const displayCountElement = document.getElementById('display-count');

    // 存储当前筛选状态
    const filterState = {
        company: 'all',
        tag: 'all',
        search: ''
    };

    // 筛选按钮点击事件
    filterButtons.forEach(button => {
        button.addEventListener('click', function () {
            const filterType = this.getAttribute('data-filter-type');
            const filterValue = this.getAttribute('data-filter-value');

            // 更新筛选状态
            filterState[filterType] = filterValue;

            // 更新按钮样式
            document.querySelectorAll(`.tag[data-filter-type="${filterType}"]`).forEach(btn => {
                btn.classList.remove('selected', 'bg-blue-100', 'text-blue-800');
                btn.classList.add('bg-gray-100', 'text-gray-800');
            });
            this.classList.add('selected', 'bg-blue-100', 'text-blue-800');
            this.classList.remove('bg-gray-100', 'text-gray-800');

            // 执行筛选
            applyFilters();
        });
    });

    // 搜索框输入事件
    searchInput.addEventListener('input', function () {
        filterState.search = this.value.toLowerCase();
        applyFilters();
    });

    // 重置筛选按钮点击事件
    resetFilterButton.addEventListener('click', function () {
        // 重置筛选状态
        filterState.company = 'all';
        filterState.tag = 'all';
        filterState.search = '';

        // 重置搜索框
        searchInput.value = '';

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

    // 应用筛选条件
    function applyFilters() {
        const rows = document.querySelectorAll('.article-row');
        let visibleCount = 0;

        rows.forEach(row => {
            const company = row.getAttribute('data-company');
            const tags = row.getAttribute('data-tags').split(',');
            const title = row.querySelector('a').getAttribute('title').toLowerCase();

            // 检查公司筛选条件
            const companyMatch = filterState.company === 'all' || company === filterState.company;

            // 检查标签筛选条件
            const tagMatch = filterState.tag === 'all' || tags.includes(filterState.tag);

            // 检查搜索条件
            const searchMatch = filterState.search === '' || title.includes(filterState.search);

            // 显示或隐藏行
            if (companyMatch && tagMatch && searchMatch) {
                row.style.display = 'table-row';
                visibleCount++;
            } else {
                row.style.display = 'none';
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