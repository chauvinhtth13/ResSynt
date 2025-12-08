// frontends/static/js/admin/study_site_inline.js
(function() {
    'use strict';
    
    console.log('=== Study Site Inline Script Loaded ===');
    
    function preventDuplicates() {
        const selects = document.querySelectorAll('select[name$="-site"]');
        
        if (selects.length === 0) return;
        
        // Thu thập các site IDs đã chọn
        const selected = [];
        selects.forEach(sel => {
            if (sel.value) selected.push(sel.value);
        });
        
        console.log('Selected sites:', selected);
        
        // Disable duplicate options
        selects.forEach((sel, idx) => {
            const current = sel.value;
            
            sel.querySelectorAll('option').forEach(opt => {
                const val = opt.value;
                
                // Reset
                opt.disabled = false;
                opt.textContent = opt.textContent.replace(' ✗', '');
                
                // Disable if selected elsewhere
                if (val && val !== current && selected.includes(val)) {
                    opt.disabled = true;
                    opt.textContent += ' ✗';
                    console.log(`Disabled "${opt.textContent}" in select #${idx}`);
                }
            });
        });
    }
    
    // Initialize
    function init() {
        setTimeout(preventDuplicates, 100);
        
        // Listen to changes
        document.addEventListener('change', e => {
            if (e.target.matches('select[name$="-site"]')) {
                console.log('Site changed!');
                preventDuplicates();
            }
        });
        
        // Listen to add/delete
        document.addEventListener('click', e => {
            if (e.target.closest('.add-row, .delete-row')) {
                setTimeout(preventDuplicates, 300);
            }
        });
    }
    
    // Run
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    window.preventDuplicates = preventDuplicates;
})();