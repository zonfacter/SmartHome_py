/**
 * Symbol Browser v4.6.0
 * Moderner TreeView für PLC-Symbole mit korrekter Type-Detection
 */

class SymbolBrowserV5 {
    constructor(options = {}) {
        this.connectionId = options.connectionId || 'plc_001';
        this.container = options.container || document.getElementById('symbol-tree');
        this.onSelect = options.onSelect || ((symbol) => console.log('Symbol selected:', symbol));

        this.symbols = [];
        this.tree = null;
        this.searchQuery = '';
        this.filterType = '';

        this.init();
    }

    init() {
        this.render();
        this.attachEvents();
        this.loadSymbols();
    }

    render() {
        this.container.innerHTML = `
            <div class="symbol-browser-v5">
                <!-- Header -->
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                        <i data-lucide="folder-tree" class="inline w-5 h-5 mr-2"></i>
                        PLC Symbole
                    </h3>
                    <button id="refresh-symbols-btn" class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600">
                        <i data-lucide="refresh-cw" class="inline w-4 h-4"></i>
                        Aktualisieren
                    </button>
                </div>

                <!-- Search & Filter -->
                <div class="space-y-2 mb-4">
                    <div class="relative">
                        <input
                            type="text"
                            id="symbol-search"
                            placeholder="Suche nach Symbol..."
                            class="w-full px-3 py-2 pl-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                        >
                        <i data-lucide="search" class="absolute left-3 top-2.5 w-4 h-4 text-gray-400"></i>
                    </div>

                    <div class="flex gap-2 flex-wrap">
                        <button class="type-filter-btn px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 hover:text-white" data-type="">
                            Alle
                        </button>
                        <button class="type-filter-btn px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 hover:text-white" data-type="BOOL">
                            BOOL
                        </button>
                        <button class="type-filter-btn px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 hover:text-white" data-type="INT">
                            INT
                        </button>
                        <button class="type-filter-btn px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 hover:text-white" data-type="REAL">
                            REAL
                        </button>
                        <button class="type-filter-btn px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 hover:bg-blue-500 hover:text-white" data-type="STRING">
                            STRING
                        </button>
                    </div>
                </div>

                <!-- Stats -->
                <div id="symbol-stats" class="text-xs text-gray-500 dark:text-gray-400 mb-3"></div>

                <!-- Tree Container -->
                <div id="symbol-tree-container" class="border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 overflow-auto max-h-96">
                    <div class="p-4 text-center text-gray-500">
                        Lade Symbole...
                    </div>
                </div>
            </div>
        `;

        // Re-initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    attachEvents() {
        // Refresh Button
        const refreshBtn = document.getElementById('refresh-symbols-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadSymbols(true));
        }

        // Search Input
        const searchInput = document.getElementById('symbol-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchQuery = e.target.value;
                this.applyFilters();
            });
        }

        // Type Filter Buttons
        const filterButtons = document.querySelectorAll('.type-filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active from all
                filterButtons.forEach(b => b.classList.remove('bg-blue-500', 'text-white'));
                // Add active to clicked
                btn.classList.add('bg-blue-500', 'text-white');

                this.filterType = btn.dataset.type;
                this.applyFilters();
            });
        });
    }

    async loadSymbols(forceRefresh = false) {
        try {
            const response = await fetch(`/api/v5/plc/symbols/tree?connection_id=${this.connectionId}&force_refresh=${forceRefresh}`);

            if (!response.ok) {
                throw new Error('Fehler beim Laden der Symbole');
            }

            const data = await response.json();
            this.tree = data.tree;
            this.renderTree();
            this.updateStats();

        } catch (error) {
            console.error('Symbol Load Error:', error);
            const container = document.getElementById('symbol-tree-container');
            if (container) {
                container.innerHTML = `
                    <div class="p-4 text-center text-red-500">
                        <i data-lucide="alert-triangle" class="inline w-5 h-5 mr-2"></i>
                        Fehler beim Laden: ${error.message}
                    </div>
                `;
            }
        }
    }

    renderTree() {
        const container = document.getElementById('symbol-tree-container');
        if (!container || !this.tree) return;

        container.innerHTML = '';
        this.renderTreeNode(this.tree, container, 0);

        // Re-initialize icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    renderTreeNode(node, parentElement, level) {
        if (!node.children || node.children.length === 0) return;

        const ul = document.createElement('ul');
        ul.className = 'space-y-1';

        node.children.forEach(child => {
            const li = document.createElement('li');

            const isLeaf = child.is_leaf;
            const hasChildren = child.children && child.children.length > 0;

            // Node Content
            const nodeDiv = document.createElement('div');
            nodeDiv.className = `flex items-center space-x-2 px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer`;
            nodeDiv.style.paddingLeft = `${level * 16 + 8}px`;

            // Expand/Collapse Icon
            if (!isLeaf && hasChildren) {
                const expandIcon = document.createElement('i');
                expandIcon.setAttribute('data-lucide', 'chevron-right');
                expandIcon.className = 'w-4 h-4 text-gray-400 expand-icon transition-transform';
                nodeDiv.appendChild(expandIcon);
            } else {
                const spacer = document.createElement('span');
                spacer.className = 'w-4 h-4';
                nodeDiv.appendChild(spacer);
            }

            // Icon
            const icon = document.createElement('i');
            icon.setAttribute('data-lucide', isLeaf ? 'tag' : 'folder');
            icon.className = `w-4 h-4 ${isLeaf ? 'text-blue-500' : 'text-yellow-500'}`;
            nodeDiv.appendChild(icon);

            // Name
            const name = document.createElement('span');
            name.textContent = child.name;
            name.className = 'text-sm text-gray-900 dark:text-white flex-1';
            nodeDiv.appendChild(name);

            // Type Badge (for leaves)
            if (isLeaf && child.type) {
                const typeBadge = document.createElement('span');
                typeBadge.textContent = child.type;
                typeBadge.className = 'text-xs px-2 py-0.5 rounded bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300';
                nodeDiv.appendChild(typeBadge);
            }

            li.appendChild(nodeDiv);

            // Child Container (hidden by default)
            if (!isLeaf && hasChildren) {
                const childContainer = document.createElement('div');
                childContainer.className = 'hidden';
                childContainer.dataset.expanded = 'false';

                // Click to expand/collapse
                nodeDiv.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const isExpanded = childContainer.dataset.expanded === 'true';

                    if (isExpanded) {
                        childContainer.classList.add('hidden');
                        childContainer.dataset.expanded = 'false';
                        const expandIcon = nodeDiv.querySelector('.expand-icon');
                        if (expandIcon) {
                            expandIcon.style.transform = 'rotate(0deg)';
                        }
                    } else {
                        childContainer.classList.remove('hidden');
                        childContainer.dataset.expanded = 'true';
                        const expandIcon = nodeDiv.querySelector('.expand-icon');
                        if (expandIcon) {
                            expandIcon.style.transform = 'rotate(90deg)';
                        }

                        // Render children lazily
                        if (childContainer.children.length === 0) {
                            this.renderTreeNode(child, childContainer, level + 1);
                        }
                    }
                });

                li.appendChild(childContainer);
            }

            // Click on leaf to select
            if (isLeaf) {
                nodeDiv.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.selectSymbol(child);
                });
            }

            ul.appendChild(li);
        });

        parentElement.appendChild(ul);
    }

    selectSymbol(symbol) {
        // Highlight selected
        document.querySelectorAll('#symbol-tree-container .bg-blue-100').forEach(el => {
            el.classList.remove('bg-blue-100', 'dark:bg-blue-900');
        });

        // Find and highlight
        const nodeElements = document.querySelectorAll('#symbol-tree-container > ul li > div');
        nodeElements.forEach(el => {
            if (el.textContent.includes(symbol.name) && el.querySelector('span').textContent === symbol.name) {
                el.classList.add('bg-blue-100', 'dark:bg-blue-900');
            }
        });

        // Call callback
        this.onSelect(symbol);
    }

    async applyFilters() {
        if (this.searchQuery) {
            // Use search API
            await this.searchSymbols(this.searchQuery);
        } else if (this.filterType) {
            // Use filter API
            await this.filterSymbols(this.filterType);
        } else {
            // Show full tree
            this.renderTree();
        }
    }

    async searchSymbols(query) {
        try {
            const response = await fetch(`/api/v5/plc/symbols/search?q=${encodeURIComponent(query)}&connection_id=${this.connectionId}`);
            const data = await response.json();

            this.renderSearchResults(data.results);
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    async filterSymbols(type) {
        try {
            const response = await fetch(`/api/v5/plc/symbols/filter/${type}?connection_id=${this.connectionId}`);
            const data = await response.json();

            this.renderSearchResults(data.results);
        } catch (error) {
            console.error('Filter error:', error);
        }
    }

    renderSearchResults(results) {
        const container = document.getElementById('symbol-tree-container');
        if (!container) return;

        container.innerHTML = '';

        if (results.length === 0) {
            container.innerHTML = '<div class="p-4 text-center text-gray-500">Keine Ergebnisse</div>';
            return;
        }

        const ul = document.createElement('ul');
        ul.className = 'space-y-1';

        results.forEach(symbol => {
            const li = document.createElement('li');

            const nodeDiv = document.createElement('div');
            nodeDiv.className = 'flex items-center space-x-2 px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer';

            const icon = document.createElement('i');
            icon.setAttribute('data-lucide', 'tag');
            icon.className = 'w-4 h-4 text-blue-500';
            nodeDiv.appendChild(icon);

            const name = document.createElement('span');
            name.textContent = symbol.name;
            name.className = 'text-sm text-gray-900 dark:text-white flex-1';
            nodeDiv.appendChild(name);

            const typeBadge = document.createElement('span');
            typeBadge.textContent = symbol.type;
            typeBadge.className = 'text-xs px-2 py-0.5 rounded bg-gray-200 dark:bg-gray-600';
            nodeDiv.appendChild(typeBadge);

            nodeDiv.addEventListener('click', () => this.selectSymbol(symbol));

            li.appendChild(nodeDiv);
            ul.appendChild(li);
        });

        container.appendChild(ul);

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        this.updateStats(results.length);
    }

    updateStats(count = null) {
        const statsEl = document.getElementById('symbol-stats');
        if (!statsEl) return;

        if (count !== null) {
            statsEl.textContent = `${count} Symbol(e) gefunden`;
        } else {
            statsEl.textContent = 'Symbole geladen';
        }
    }
}

// Export for use
window.SymbolBrowserV5 = SymbolBrowserV5;
