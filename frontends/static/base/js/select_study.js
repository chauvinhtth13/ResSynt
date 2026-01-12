// frontends/static/base/js/select_study.js
(() => {
    'use strict';

    class StudySearcher {
        constructor() {
            // DOM elements - cache once
            this.searchInput = document.getElementById('searchInput');
            this.listBody = document.getElementById('studyTableBody');
            this.paginationControls = document.getElementById('paginationControls');
            this.pageSizeSelect = document.getElementById('pageSizeSelect');
            this.defaultEmptyState = document.getElementById('emptyStateDefault');
            
            // Cache pagination info elements
            this.startEl = document.getElementById('showingStart');
            this.endEl = document.getElementById('showingEnd');
            this.totalEl = document.getElementById('totalStudies');
            
            // Pre-create search empty state (reuse instead of recreate)
            this.searchEmptyState = this.createSearchEmptyState();
            
            // Pagination settings
            this.itemsPerPage = 5;
            this.currentPage = 1;
            this.totalPages = 0;
            
            // Data arrays
            this.allItems = [];
            this.filteredItems = [];
            
            // Track visible items for efficient updates
            this.visibleSet = new Set();

            // Debounce with bound handler
            this.searchTimer = null;
            this.debounceDelay = 150; // Reduced for snappier response
            
            // Bound handlers (avoid creating new functions)
            this.boundHandleSearch = this.handleSearch.bind(this);
            this.boundOnPaginationClick = this.onPaginationClick.bind(this);
            
            // Animation frame for smooth rendering
            this.rafId = null;
            
            // Last search term to avoid redundant searches
            this.lastSearchTerm = '';

            if (!this.searchInput || !this.listBody) {
                return;
            }

            this.initialize();
        }

        createSearchEmptyState() {
            const el = document.createElement('div');
            el.className = 'study-list__empty';
            el.id = 'emptyStateSearch';
            el.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state__icon">
                        <i class="bi bi-search" aria-hidden="true"></i>
                    </div>
                    <h3 class="empty-state__title">No matching studies</h3>
                    <p class="empty-state__text">Try a different search term</p>
                </div>
            `;
            return el;
        }

        initialize() {
            // Cache all study items using NodeList directly (faster than Array.from for iteration)
            const items = this.listBody.querySelectorAll('.study-item[data-study-id]');
            const len = items.length;
            this.allItems = new Array(len);
            
            // Pre-cache text content for faster search
            for (let i = 0; i < len; i++) {
                const item = items[i];
                this.allItems[i] = item;
                
                // Cache search text - combine code and name
                const codeEl = item.querySelector('[data-col="code"]');
                const nameEl = item.querySelector('[data-col="name"]');
                item._searchText = (
                    (codeEl ? codeEl.textContent.trim() : '') + ' ' + 
                    (nameEl ? nameEl.textContent.trim() : '')
                ).toLowerCase();
                
                // Cache index for O(1) lookup
                item._index = i;
            }
            
            // Initialize filtered as reference (not copy) when no filter
            this.filteredItems = this.allItems;
            
            // Hide default empty state if we have items
            if (len > 0 && this.defaultEmptyState) {
                this.defaultEmptyState.hidden = true;
            }
            
            this.attachEvents();
            this.updateDisplay();
        }

        attachEvents() {
            // Search input with debounce
            this.searchInput.addEventListener('input', () => {
                clearTimeout(this.searchTimer);
                this.searchTimer = setTimeout(this.boundHandleSearch, this.debounceDelay);
            });
            
            // Clear on Escape - use keydown for immediate response
            this.searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.searchInput.value) {
                    e.preventDefault();
                    this.searchInput.value = '';
                    this.lastSearchTerm = '';
                    this.filteredItems = this.allItems;
                    this.currentPage = 1;
                    this.scheduleUpdate();
                }
            });

            // Page size selector
            if (this.pageSizeSelect) {
                this.pageSizeSelect.addEventListener('change', (e) => {
                    this.itemsPerPage = e.target.value | 0; // Faster parseInt
                    this.currentPage = 1;
                    this.scheduleUpdate();
                });
            }
            
            // Event delegation for pagination (single listener instead of per-button)
            if (this.paginationControls) {
                this.paginationControls.addEventListener('click', this.boundOnPaginationClick);
            }
        }

        onPaginationClick(e) {
            const link = e.target.closest('.page-link');
            if (!link) return;
            
            e.preventDefault();
            
            const li = link.parentElement;
            if (li.classList.contains('disabled') || li.classList.contains('active')) {
                return;
            }
            
            const action = link.dataset.action;
            if (action === 'prev') {
                this.currentPage--;
            } else if (action === 'next') {
                this.currentPage++;
            } else if (action) {
                this.currentPage = action | 0;
            }
            
            this.scheduleUpdate();
        }

        handleSearch() {
            const filter = this.searchInput.value.toLowerCase().trim();
            
            // Skip if search term hasn't changed
            if (filter === this.lastSearchTerm) {
                return;
            }
            this.lastSearchTerm = filter;
            
            if (!filter) {
                // No filter - use original array reference
                this.filteredItems = this.allItems;
            } else {
                // Filter with optimized loop
                const results = [];
                const items = this.allItems;
                const len = items.length;
                
                for (let i = 0; i < len; i++) {
                    if (items[i]._searchText.indexOf(filter) !== -1) {
                        results.push(items[i]);
                    }
                }
                this.filteredItems = results;
            }

            this.currentPage = 1;
            this.scheduleUpdate();
        }

        scheduleUpdate() {
            if (this.rafId) {
                cancelAnimationFrame(this.rafId);
            }
            this.rafId = requestAnimationFrame(() => {
                this.rafId = null;
                this.updateDisplay();
            });
        }

        updateDisplay() {
            const allLen = this.allItems.length;
            const filteredLen = this.filteredItems.length;
            
            // Calculate what should be visible
            const newVisibleSet = new Set();
            let startIndex = 0;
            let endIndex = 0;
            
            if (filteredLen > 0) {
                this.totalPages = Math.ceil(filteredLen / this.itemsPerPage);
                startIndex = (this.currentPage - 1) * this.itemsPerPage;
                endIndex = Math.min(startIndex + this.itemsPerPage, filteredLen);
                
                for (let i = startIndex; i < endIndex; i++) {
                    newVisibleSet.add(this.filteredItems[i]);
                }
            } else {
                this.totalPages = 0;
            }
            
            // Diff-based update: only modify changed items
            // Hide items that were visible but shouldn't be
            for (const item of this.visibleSet) {
                if (!newVisibleSet.has(item)) {
                    item.classList.add('hidden');
                }
            }
            
            // Show items that should be visible but aren't
            for (const item of newVisibleSet) {
                if (!this.visibleSet.has(item)) {
                    item.classList.remove('hidden');
                }
            }
            
            // Update visible set
            this.visibleSet = newVisibleSet;
            
            // Handle empty states
            this.updateEmptyStates(allLen, filteredLen);
            
            // Update pagination info
            this.updatePaginationInfo(
                filteredLen === 0 ? 0 : startIndex + 1,
                endIndex,
                filteredLen
            );
            
            // Render pagination controls
            this.renderPagination();
        }

        updateEmptyStates(allLen, filteredLen) {
            // Default empty state (no studies at all)
            if (this.defaultEmptyState) {
                this.defaultEmptyState.hidden = allLen > 0;
            }
            
            // Search empty state (no results for search)
            const showSearchEmpty = allLen > 0 && filteredLen === 0;
            
            if (showSearchEmpty) {
                if (!this.searchEmptyState.parentNode) {
                    this.listBody.appendChild(this.searchEmptyState);
                }
            } else if (this.searchEmptyState.parentNode) {
                this.searchEmptyState.remove();
            }
        }

        updatePaginationInfo(start, end, total) {
            if (this.startEl) this.startEl.textContent = start;
            if (this.endEl) this.endEl.textContent = end;
            if (this.totalEl) this.totalEl.textContent = total;
        }

        renderPagination() {
            if (!this.paginationControls) return;

            const totalPages = this.totalPages;
            const currentPage = this.currentPage;
            
            // Build HTML string (faster than DOM manipulation for small elements)
            const parts = [];
            
            // Previous button
            parts.push(this.getNavButtonHtml('prev', '‹', currentPage === 1 || totalPages === 0));
            
            // Page numbers
            if (totalPages <= 1) {
                parts.push(this.getPageButtonHtml(1, currentPage === 1, totalPages === 0));
            } else {
                this.appendPageNumbersHtml(parts, totalPages, currentPage);
            }
            
            // Next button
            parts.push(this.getNavButtonHtml('next', '›', currentPage >= totalPages || totalPages <= 1));
            
            this.paginationControls.innerHTML = parts.join('');
        }

        appendPageNumbersHtml(parts, totalPages, currentPage) {
            const maxVisible = 5;
            
            if (totalPages <= maxVisible) {
                for (let i = 1; i <= totalPages; i++) {
                    parts.push(this.getPageButtonHtml(i, currentPage === i, false));
                }
                return;
            }

            if (currentPage <= 3) {
                for (let i = 1; i <= 3; i++) {
                    parts.push(this.getPageButtonHtml(i, currentPage === i, false));
                }
                parts.push('<li class="page-item disabled"><span class="page-link">…</span></li>');
                parts.push(this.getPageButtonHtml(totalPages, false, false));
                
            } else if (currentPage >= totalPages - 2) {
                parts.push(this.getPageButtonHtml(1, false, false));
                parts.push('<li class="page-item disabled"><span class="page-link">…</span></li>');
                for (let i = totalPages - 2; i <= totalPages; i++) {
                    parts.push(this.getPageButtonHtml(i, currentPage === i, false));
                }
                
            } else {
                parts.push(this.getPageButtonHtml(1, false, false));
                parts.push('<li class="page-item disabled"><span class="page-link">…</span></li>');
                for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                    parts.push(this.getPageButtonHtml(i, currentPage === i, false));
                }
                parts.push('<li class="page-item disabled"><span class="page-link">…</span></li>');
                parts.push(this.getPageButtonHtml(totalPages, false, false));
            }
        }

        getPageButtonHtml(pageNum, isActive, isDisabled) {
            const classes = ['page-item'];
            if (isActive) classes.push('active');
            if (isDisabled) classes.push('disabled');
            
            return `<li class="${classes.join(' ')}"><a class="page-link" href="#" data-action="${pageNum}">${pageNum}</a></li>`;
        }

        getNavButtonHtml(action, symbol, disabled) {
            const disabledClass = disabled ? ' disabled' : '';
            return `<li class="page-item${disabledClass}"><a class="page-link" href="#" data-action="${action}">${symbol}</a></li>`;
        }
    }

    // Initialize with optimal timing
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new StudySearcher(), { once: true });
    } else {
        new StudySearcher();
    }
})();