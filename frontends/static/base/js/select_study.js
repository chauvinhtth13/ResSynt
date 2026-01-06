// frontends/static/base/js/select_study.js
(() => {
    'use strict';

    class StudySearcher {
        constructor() {
            // DOM elements
            this.searchInput = document.getElementById('searchInput');
            this.listBody = document.getElementById('studyTableBody');
            this.paginationControls = document.getElementById('paginationControls');
            this.pageSizeSelect = document.getElementById('pageSizeSelect');
            this.defaultEmptyState = document.getElementById('emptyStateDefault');
            this.searchEmptyState = null;
            
            // Pagination settings
            this.itemsPerPage = 5;
            this.currentPage = 1;
            this.allItems = [];
            this.filteredItems = [];

            // Debounce
            this.searchTimer = null;
            this.debounceDelay = 200;
            
            // Animation frame for smooth rendering
            this.rafId = null;

            if (!this.searchInput || !this.listBody) {
                return;
            }

            this.initialize();
        }

        initialize() {
            // Cache all study items
            this.allItems = Array.from(this.listBody.querySelectorAll('.study-item[data-study-id]'));
            this.filteredItems = [...this.allItems];
            
            // Pre-cache text content for faster search
            this.allItems.forEach(item => {
                const codeEl = item.querySelector('[data-col="code"]');
                const nameEl = item.querySelector('[data-col="name"]');
                item._searchText = (
                    (codeEl?.textContent || '') + ' ' + 
                    (nameEl?.textContent || '')
                ).toLowerCase();
            });
            
            // Hide default empty state if we have items
            if (this.allItems.length > 0 && this.defaultEmptyState) {
                this.defaultEmptyState.style.display = 'none';
            }
            
            this.attachEvents();
            this.updateDisplay();
        }

        attachEvents() {
            // Optimized search with debounce
            this.searchInput.addEventListener('input', this.onSearchInput.bind(this));
            
            // Clear on Escape
            this.searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.searchInput.value) {
                    e.preventDefault();
                    this.searchInput.value = '';
                    this.handleSearch();
                }
            });

            // Page size selector
            if (this.pageSizeSelect) {
                this.pageSizeSelect.addEventListener('change', (e) => {
                    this.setPageSize(e.target.value);
                });
            }
        }

        onSearchInput() {
            clearTimeout(this.searchTimer);
            this.searchTimer = setTimeout(() => this.handleSearch(), this.debounceDelay);
        }

        handleSearch() {
            const filter = this.searchInput.value.toLowerCase().trim();
            
            // Use cached search text for performance
            if (filter) {
                this.filteredItems = this.allItems.filter(item => 
                    item._searchText.includes(filter)
                );
            } else {
                this.filteredItems = [...this.allItems];
            }

            this.currentPage = 1;
            this.scheduleUpdate();
        }

        scheduleUpdate() {
            // Cancel previous frame
            if (this.rafId) {
                cancelAnimationFrame(this.rafId);
            }
            // Schedule update on next frame for smooth rendering
            this.rafId = requestAnimationFrame(() => this.updateDisplay());
        }

        updateDisplay() {
            // Hide all items using CSS class (faster than style manipulation)
            this.allItems.forEach(item => {
                item.classList.add('hidden');
            });

            // Remove search empty state
            this.removeSearchEmptyState();
            
            // Handle empty states
            if (this.allItems.length === 0) {
                // No studies at all - show default empty
                if (this.defaultEmptyState) {
                    this.defaultEmptyState.style.display = '';
                }
                this.updatePaginationInfo(0, 0, 0);
                this.renderPagination();
                return;
            }
            
            // Hide default empty state
            if (this.defaultEmptyState) {
                this.defaultEmptyState.style.display = 'none';
            }

            // No search results
            if (this.filteredItems.length === 0) {
                this.showSearchEmptyState();
                this.updatePaginationInfo(0, 0, 0);
                this.renderPagination();
                return;
            }

            // Calculate pagination
            const totalPages = Math.ceil(this.filteredItems.length / this.itemsPerPage);
            const startIndex = (this.currentPage - 1) * this.itemsPerPage;
            const endIndex = Math.min(startIndex + this.itemsPerPage, this.filteredItems.length);

            // Show current page items
            for (let i = startIndex; i < endIndex; i++) {
                this.filteredItems[i].classList.remove('hidden');
            }

            this.updatePaginationInfo(startIndex + 1, endIndex, this.filteredItems.length);
            this.renderPagination();
        }

        showSearchEmptyState() {
            if (!this.searchEmptyState) {
                this.searchEmptyState = document.createElement('div');
                this.searchEmptyState.className = 'study-list__empty';
                this.searchEmptyState.id = 'emptyStateSearch';
                this.searchEmptyState.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state__icon">
                            <i class="bi bi-search" aria-hidden="true"></i>
                        </div>
                        <h3 class="empty-state__title">No matching studies</h3>
                        <p class="empty-state__text">Try a different search term</p>
                    </div>
                `;
            }
            this.listBody.appendChild(this.searchEmptyState);
        }

        removeSearchEmptyState() {
            if (this.searchEmptyState && this.searchEmptyState.parentNode) {
                this.searchEmptyState.remove();
            }
        }

        updatePaginationInfo(start, end, total) {
            const startEl = document.getElementById('showingStart');
            const endEl = document.getElementById('showingEnd');
            const totalEl = document.getElementById('totalStudies');

            if (startEl) startEl.textContent = total === 0 ? 0 : start;
            if (endEl) endEl.textContent = end;
            if (totalEl) totalEl.textContent = total;
        }

        renderPagination() {
            if (!this.paginationControls) return;

            const totalPages = Math.ceil(this.filteredItems.length / this.itemsPerPage);
            this.paginationControls.innerHTML = '';

            // Use DocumentFragment for batch DOM updates
            const fragment = document.createDocumentFragment();

            // Previous button - always show, disabled when no prev
            fragment.appendChild(
                this.createNavButton('‹', this.currentPage === 1 || totalPages === 0, -1)
            );

            // Page numbers - show at least page 1 placeholder when empty
            if (totalPages <= 1) {
                fragment.appendChild(this.createPageButton(1, totalPages === 0));
            } else {
                this.appendPageNumbers(fragment, totalPages);
            }

            // Next button - always show, disabled when no next
            fragment.appendChild(
                this.createNavButton('›', this.currentPage === totalPages || totalPages <= 1, 1)
            );

            this.paginationControls.appendChild(fragment);
        }

        appendPageNumbers(fragment, totalPages) {
            const maxVisible = 5;
            
            if (totalPages <= maxVisible) {
                for (let i = 1; i <= totalPages; i++) {
                    fragment.appendChild(this.createPageButton(i));
                }
                return;
            }

            if (this.currentPage <= 3) {
                for (let i = 1; i <= 3; i++) {
                    fragment.appendChild(this.createPageButton(i));
                }
                fragment.appendChild(this.createEllipsis());
                fragment.appendChild(this.createPageButton(totalPages));
                
            } else if (this.currentPage >= totalPages - 2) {
                fragment.appendChild(this.createPageButton(1));
                fragment.appendChild(this.createEllipsis());
                for (let i = totalPages - 2; i <= totalPages; i++) {
                    fragment.appendChild(this.createPageButton(i));
                }
                
            } else {
                fragment.appendChild(this.createPageButton(1));
                fragment.appendChild(this.createEllipsis());
                for (let i = this.currentPage - 1; i <= this.currentPage + 1; i++) {
                    fragment.appendChild(this.createPageButton(i));
                }
                fragment.appendChild(this.createEllipsis());
                fragment.appendChild(this.createPageButton(totalPages));
            }
        }

        createPageButton(pageNum, forceDisabled = false) {
            const li = document.createElement('li');
            const isActive = this.currentPage === pageNum && !forceDisabled;
            const isDisabled = forceDisabled;
            
            li.className = 'page-item' + (isActive ? ' active' : '') + (isDisabled ? ' disabled' : '');
            
            const btn = document.createElement('a');
            btn.className = 'page-link';
            btn.href = '#';
            btn.textContent = pageNum;
            
            if (!isActive && !isDisabled) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.goToPage(pageNum);
                });
            }
            
            li.appendChild(btn);
            return li;
        }

        createNavButton(symbol, disabled, direction) {
            const li = document.createElement('li');
            li.className = 'page-item' + (disabled ? ' disabled' : '');
            
            const btn = document.createElement('a');
            btn.className = 'page-link';
            btn.href = '#';
            btn.innerHTML = symbol;
            
            if (!disabled) {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.goToPage(this.currentPage + direction);
                });
            }
            
            li.appendChild(btn);
            return li;
        }

        createEllipsis() {
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = '<span class="page-link">…</span>';
            return li;
        }

        goToPage(page) {
            this.currentPage = page;
            this.scheduleUpdate();
        }

        setPageSize(size) {
            this.itemsPerPage = parseInt(size, 10);
            this.currentPage = 1;
            this.scheduleUpdate();
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new StudySearcher());
    } else {
        new StudySearcher();
    }
})();