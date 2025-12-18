// Load HTML components into placeholders by element ID
async function loadComponent(elementId, componentPath) {
    try {
        const resp = await fetch(componentPath, {cache: 'no-store'});
        if (!resp.ok) throw new Error(`Failed to fetch ${componentPath}: ${resp.status}`);
        const html = await resp.text();
        const el = document.getElementById(elementId);
        if (el) el.innerHTML = html;
        if (elementId === 'navbar-placeholder') setActiveNavLink();
    } catch (err) {
        console.error('Error loading component', componentPath, err);
    }
}

// Mark current page's nav link as active
function setActiveNavLink() {
    // current page file name (e.g., test8.html)
    const path = window.location.pathname;
    const page = path.split('/').pop() || 'index.html';
    const links = document.querySelectorAll('#navbar-placeholder .nav-link');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (!href) return;
        // compare only filename portion
        const linkPage = href.split('/').pop();
        if (linkPage === page) link.classList.add('active');
        else link.classList.remove('active');
    });
}

// Convenience: load multiple components when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('navbar-placeholder')) {
        loadComponent('navbar-placeholder', 'components/navbar.html');
    }
    if (document.getElementById('footer-placeholder')) {
        loadComponent('footer-placeholder', 'components/footer.html');
    }
    if (document.getElementById('header-info-placeholder')) {
        loadComponent('header-info-placeholder', 'components/header-info.html');
    }
});

// Helpful dev message if file:// is used
if (window.location.protocol === 'file:') {
    // Note: fetch of local files may be blocked by browser. Recommend using an HTTP server.
    console.warn('You are opening pages via file:// — components loaded by fetch may fail. Run a local HTTP server (Live Server or `python -m http.server`) to enable components.');
}
