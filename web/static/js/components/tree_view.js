/**
 * TreeView Component v1.0.0
 * Hierarchische Tree-Ansicht für PLC-Symbole und MQTT-Topics
 *
 * Features:
 * - Collapsible Nodes
 * - Search/Filter
 * - Drag & Drop Support
 * - Icons nach Datentyp
 * - Lazy Loading
 */

class TreeView {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`TreeView: Container #${containerId} nicht gefunden!`);
            return;
        }

        this.options = {
            draggable: options.draggable !== false, // Default: true
            showIcons: options.showIcons !== false, // Default: true
            searchable: options.searchable !== false, // Default: true
            expandLevel: options.expandLevel || 1, // Wie viele Ebenen initial expandiert
            onNodeClick: options.onNodeClick || null,
            onNodeDragStart: options.onNodeDragStart || null,
            ...options
        };

        this.data = null;
        this.expandedNodes = new Set();
        this.selectedNode = null;
        this.filteredData = null;

        this._init();
    }

    _init() {
        // Container vorbereiten
        this.container.className = 'tree-view';
        this.container.innerHTML = '';

        // Optionale Suchleiste
        if (this.options.searchable) {
            this._createSearchBar();
        }

        // Tree-Container
        this.treeContainer = document.createElement('div');
        this.treeContainer.className = 'tree-container overflow-auto max-h-96 border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-white dark:bg-gray-800';
        this.container.appendChild(this.treeContainer);
    }

    _createSearchBar() {
        const searchBar = document.createElement('div');
        searchBar.className = 'mb-2';
        searchBar.innerHTML = `
            <input
                type="text"
                class="tree-search w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                placeholder="Suchen..."
            />
        `;
        this.container.insertBefore(searchBar, this.container.firstChild);

        const input = searchBar.querySelector('.tree-search');
        input.addEventListener('input', (e) => this._onSearch(e.target.value));
    }

    _onSearch(query) {
        if (!query.trim()) {
            this.filteredData = null;
            this.render(this.data);
            return;
        }

        // Filtere Tree-Daten
        this.filteredData = this._filterTree(this.data, query.toLowerCase());
        this.render(this.filteredData);
    }

    _filterTree(nodes, query) {
        if (!Array.isArray(nodes)) return [];

        return nodes.filter(node => {
            // Prüfe ob Node selbst matcht
            const nameMatches = node.name.toLowerCase().includes(query);

            // Prüfe Kinder
            if (node.children) {
                const filteredChildren = this._filterTree(node.children, query);
                if (filteredChildren.length > 0) {
                    return true; // Parent behalten wenn Kinder matchen
                }
            }

            return nameMatches;
        }).map(node => {
            // Wenn Node Kinder hat, filtere diese auch
            if (node.children) {
                return {
                    ...node,
                    children: this._filterTree(node.children, query)
                };
            }
            return node;
        });
    }

    /**
     * Rendert den Tree
     * @param {Array} treeData - Array von Tree-Nodes
     */
    render(treeData) {
        if (!treeData || treeData.length === 0) {
            this.treeContainer.innerHTML = '<div class="text-gray-500 dark:text-gray-400 p-4 text-center">Keine Daten</div>';
            return;
        }

        this.data = treeData;
        this.treeContainer.innerHTML = '';

        // Rendere Top-Level Nodes
        const ul = document.createElement('ul');
        ul.className = 'tree-root';

        treeData.forEach(node => {
            const li = this._renderNode(node, 0);
            ul.appendChild(li);
        });

        this.treeContainer.appendChild(ul);

        // Icons refreshen
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    _renderNode(node, level) {
        const li = document.createElement('li');
        li.className = 'tree-node';
        li.setAttribute('data-node-path', node.full_path || node.name);

        const isExpanded = this.expandedNodes.has(node.full_path || node.name) || level < this.options.expandLevel;
        const hasChildren = node.children && node.children.length > 0;
        const isLeaf = node.type === 'symbol' || !hasChildren;

        // Node-Wrapper
        const nodeDiv = document.createElement('div');
        nodeDiv.className = `tree-node-content flex items-center py-1 px-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded cursor-pointer ${
            this.selectedNode === node.full_path ? 'bg-blue-100 dark:bg-blue-900' : ''
        }`;

        // Expand/Collapse Icon
        if (!isLeaf) {
            const expandIcon = document.createElement('i');
            expandIcon.setAttribute('data-lucide', isExpanded ? 'chevron-down' : 'chevron-right');
            expandIcon.className = 'w-4 h-4 mr-1 text-gray-500 flex-shrink-0';
            nodeDiv.appendChild(expandIcon);

            expandIcon.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNode(node.full_path || node.name);
            });
        } else {
            // Spacer für Blätter
            const spacer = document.createElement('span');
            spacer.className = 'w-4 mr-1 flex-shrink-0';
            nodeDiv.appendChild(spacer);
        }

        // Type-Icon
        if (this.options.showIcons) {
            const typeIcon = document.createElement('i');
            typeIcon.setAttribute('data-lucide', this._getIconForType(node));
            typeIcon.className = `w-4 h-4 mr-2 ${this._getColorForType(node)} flex-shrink-0`;
            nodeDiv.appendChild(typeIcon);
        }

        // Name
        const nameSpan = document.createElement('span');
        nameSpan.className = 'text-sm text-gray-900 dark:text-white flex-grow';
        nameSpan.textContent = node.name;
        nodeDiv.appendChild(nameSpan);

        // Data-Type Badge (nur für Symbole)
        if (node.data_type && node.type === 'symbol') {
            const typeBadge = document.createElement('span');
            typeBadge.className = 'ml-2 px-2 py-0.5 text-xs font-mono bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded';
            typeBadge.textContent = node.data_type;
            nodeDiv.appendChild(typeBadge);
        }

        // Drag & Drop Support
        if (this.options.draggable && isLeaf) {
            nodeDiv.draggable = true;
            nodeDiv.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('application/json', JSON.stringify({
                    type: node.type,
                    path: node.full_path,
                    data_type: node.data_type,
                    name: node.name
                }));

                if (this.options.onNodeDragStart) {
                    this.options.onNodeDragStart(node, e);
                }
            });
            nodeDiv.style.cursor = 'grab';
        }

        // Click Handler
        nodeDiv.addEventListener('click', () => {
            this.selectNode(node.full_path || node.name);

            if (this.options.onNodeClick) {
                this.options.onNodeClick(node);
            }
        });

        li.appendChild(nodeDiv);

        // Children (wenn vorhanden und expandiert)
        if (hasChildren && isExpanded) {
            const childrenUl = document.createElement('ul');
            childrenUl.className = 'ml-4 mt-1';

            node.children.forEach(child => {
                const childLi = this._renderNode(child, level + 1);
                childrenUl.appendChild(childLi);
            });

            li.appendChild(childrenUl);
        }

        return li;
    }

    _getIconForType(node) {
        if (node.type === 'folder') return 'folder';
        if (node.type === 'symbol') {
            // Icons basierend auf Datentyp
            const type = (node.data_type || '').toUpperCase();
            if (type.includes('BOOL')) return 'toggle-left';
            if (type.includes('INT') || type.includes('DINT')) return 'hash';
            if (type.includes('REAL') || type.includes('LREAL')) return 'activity';
            if (type.includes('STRING')) return 'type';
            return 'file-code';
        }
        return 'file';
    }

    _getColorForType(node) {
        const type = (node.data_type || '').toUpperCase();
        if (type.includes('BOOL')) return 'text-green-500';
        if (type.includes('INT') || type.includes('DINT')) return 'text-blue-500';
        if (type.includes('REAL') || type.includes('LREAL')) return 'text-purple-500';
        if (type.includes('STRING')) return 'text-yellow-500';
        if (node.type === 'folder') return 'text-gray-500';
        return 'text-gray-400';
    }

    toggleNode(nodePath) {
        if (this.expandedNodes.has(nodePath)) {
            this.expandedNodes.delete(nodePath);
        } else {
            this.expandedNodes.add(nodePath);
        }

        this.render(this.filteredData || this.data);
    }

    selectNode(nodePath) {
        this.selectedNode = nodePath;
        this.render(this.filteredData || this.data);
    }

    expandAll() {
        const collectPaths = (nodes, paths = []) => {
            nodes.forEach(node => {
                if (node.children && node.children.length > 0) {
                    paths.push(node.full_path || node.name);
                    collectPaths(node.children, paths);
                }
            });
            return paths;
        };

        const allPaths = collectPaths(this.data || []);
        allPaths.forEach(path => this.expandedNodes.add(path));
        this.render(this.filteredData || this.data);
    }

    collapseAll() {
        this.expandedNodes.clear();
        this.render(this.filteredData || this.data);
    }
}

// Export für Module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TreeView;
}
