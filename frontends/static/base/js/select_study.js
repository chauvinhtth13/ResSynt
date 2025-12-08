// frontends\static\js\default\select_study.js
(() => {
    class StudySearcher {
        constructor() {
            this.searchInput = document.getElementById('searchInput');
            this.table = document.querySelector('.table');
            this.tbody = document.getElementById('studyTableBody');
            this.paginationControls = document.getElementById('paginationControls');
            this.noResultsRow = null;
            
            // Pagination settings
            this.itemsPerPage = 6;
            this.currentPage = 1;
            this.allRows = [];
            this.filteredRows = [];

            if (!this.searchInput || !this.tbody) {
                console.error('StudySearcher: Required elements not found.');
                return;
            }

            this.initialize();
        }

        initialize() {
            // Lấy tất cả <tr> có data-col="code" (chỉ study rows thật)
            this.allRows = Array.from(this.tbody.querySelectorAll('tr')).filter(row => {
                return row.querySelector('[data-col="code"]') !== null;
            });
            
            this.filteredRows = [...this.allRows];
            
            console.log(`Found ${this.allRows.length} study rows`);
            
            this.attachEvents();
            this.updateDisplay();
        }

        attachEvents() {
            this.searchInput.addEventListener('input', this.handleSearch.bind(this));
        }

        handleSearch() {
            const filter = this.searchInput.value.toLowerCase().trim();
            
            console.log(`Searching for: "${filter}"`);
            
            // Remove previous no-results row
            if (this.noResultsRow) {
                this.noResultsRow.remove();
                this.noResultsRow = null;
            }

            // Filter rows based on code and name
            this.filteredRows = this.allRows.filter(row => {
                const idCell = row.querySelector('[data-col="code"]');
                const nameCell = row.querySelector('[data-col="name"]');
                
                const idText = idCell ? idCell.textContent.toLowerCase().trim() : '';
                const nameText = nameCell ? nameCell.textContent.toLowerCase().trim() : '';

                return idText.includes(filter) || nameText.includes(filter);
            });

            console.log(`Found ${this.filteredRows.length} matching rows`);

            // Reset to page 1 when searching
            this.currentPage = 1;
            this.updateDisplay();
        }

        updateDisplay() {
            // Hide all rows first
            this.allRows.forEach(row => {
                row.style.display = 'none';
            });

            // Remove old no-results row if exists
            if (this.noResultsRow) {
                this.noResultsRow.remove();
                this.noResultsRow = null;
            }

            // Check if no results
            if (this.filteredRows.length === 0) {
                this.noResultsRow = document.createElement('tr');
                this.noResultsRow.innerHTML = '<td colspan="5" class="text-center">No matching studies found</td>';
                this.tbody.appendChild(this.noResultsRow);
                
                this.updatePaginationInfo(0, 0, 0);
                this.renderPagination();
                return;
            }

            // Calculate pagination
            const totalPages = Math.ceil(this.filteredRows.length / this.itemsPerPage);
            const startIndex = (this.currentPage - 1) * this.itemsPerPage;
            const endIndex = Math.min(startIndex + this.itemsPerPage, this.filteredRows.length);

            // Show current page rows
            for (let i = startIndex; i < endIndex; i++) {
                this.filteredRows[i].style.display = '';
            }

            // Update info and pagination
            this.updatePaginationInfo(startIndex + 1, endIndex, this.filteredRows.length);
            this.renderPagination();
        }

        updatePaginationInfo(start, end, total) {
            const startEl = document.getElementById('showingStart');
            const endEl = document.getElementById('showingEnd');
            const totalEl = document.getElementById('totalStudies');

            if (startEl) startEl.textContent = start;
            if (endEl) endEl.textContent = end;
            if (totalEl) totalEl.textContent = total;
        }

        renderPagination() {
            if (!this.paginationControls) return;

            const totalPages = Math.ceil(this.filteredRows.length / this.itemsPerPage);
            this.paginationControls.innerHTML = '';

            // If only 1 page or less, don't show pagination
            if (totalPages <= 1) return;

            // Previous button
            this.paginationControls.appendChild(
                this.createPaginationButton('Previous', 'Prev', this.currentPage === 1, () => {
                    if (this.currentPage > 1) this.goToPage(this.currentPage - 1);
                })
            );

            // Page numbers
            this.renderPageNumbers(totalPages);

            // Next button
            this.paginationControls.appendChild(
                this.createPaginationButton('Next', 'Next', this.currentPage === totalPages, () => {
                    if (this.currentPage < totalPages) this.goToPage(this.currentPage + 1);
                })
            );
        }

        renderPageNumbers(totalPages) {
            const maxVisibleButtons = 7;
            
            // If total pages <= 7, show all
            if (totalPages <= maxVisibleButtons) {
                for (let i = 1; i <= totalPages; i++) {
                    this.paginationControls.appendChild(this.createPageNumberButton(i));
                }
                return;
            }

            // Logic for many pages
            if (this.currentPage <= 4) {
                // Beginning: 1 2 3 [4] 5 ... 20
                for (let i = 1; i <= 5; i++) {
                    this.paginationControls.appendChild(this.createPageNumberButton(i));
                }
                this.paginationControls.appendChild(this.createEllipsis());
                this.paginationControls.appendChild(this.createPageNumberButton(totalPages));
                
            } else if (this.currentPage >= totalPages - 3) {
                // End: 1 ... 16 [17] 18 19 20
                this.paginationControls.appendChild(this.createPageNumberButton(1));
                this.paginationControls.appendChild(this.createEllipsis());
                
                for (let i = totalPages - 4; i <= totalPages; i++) {
                    this.paginationControls.appendChild(this.createPageNumberButton(i));
                }
                
            } else {
                // Middle: 1 ... 8 [9] 10 ... 20
                this.paginationControls.appendChild(this.createPageNumberButton(1));
                this.paginationControls.appendChild(this.createEllipsis());
                
                for (let i = this.currentPage - 1; i <= this.currentPage + 1; i++) {
                    this.paginationControls.appendChild(this.createPageNumberButton(i));
                }
                
                this.paginationControls.appendChild(this.createEllipsis());
                this.paginationControls.appendChild(this.createPageNumberButton(totalPages));
            }
        }

        createPageNumberButton(pageNum) {
            const li = document.createElement('li');
            li.className = `page-item ${this.currentPage === pageNum ? 'active' : ''}`;
            
            const a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.textContent = pageNum;
            a.setAttribute('aria-label', `Page ${pageNum}`);
            
            if (this.currentPage !== pageNum) {
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.goToPage(pageNum);
                });
            } else {
                a.setAttribute('aria-current', 'page');
            }
            
            li.appendChild(a);
            return li;
        }

        createPaginationButton(label, symbol, disabled, onClick) {
            const li = document.createElement('li');
            li.className = `page-item ${disabled ? 'disabled' : ''}`;
            
            const a = document.createElement('a');
            a.className = 'page-link';
            a.href = '#';
            a.setAttribute('aria-label', label);
            a.innerHTML = `<span aria-hidden="true">${symbol}</span>`;
            
            if (!disabled) {
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    onClick();
                });
            }
            
            li.appendChild(a);
            return li;
        }

        createEllipsis() {
            const li = document.createElement('li');
            li.className = 'page-item disabled';
            li.innerHTML = '<span class="page-link">...</span>';
            return li;
        }

        goToPage(page) {
            this.currentPage = page;
            this.updateDisplay();
            
            // Scroll to top of table
            if (this.table) {
                this.table.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        new StudySearcher();
    });
})();