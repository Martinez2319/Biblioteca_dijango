/**
 * Biblioteca Virtual - JavaScript Común
 * Funciones compartidas entre todas las páginas
 */

// === TEMA CLARO/OSCURO ===
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = savedTheme || (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}

// Inicializar tema al cargar
initTheme();

// Listener para el botón de tema
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('themeToggle');
    if (toggle) {
        toggle.addEventListener('click', toggleTheme);
    }
});

// === UTILIDADES ===
const PLACEHOLDER_IMG = 'https://placehold.co/180x250/e2e8f0/64748b?text=Sin+Portada';

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function convertDriveImageUrl(url) {
    if (!url) return url;
    const match = url.match(/drive\.google\.com\/file\/d\/([^/]+)/);
    return match ? `https://lh3.googleusercontent.com/d/${match[1]}` : url;
}

function convertPdfUrl(url) {
    if (!url) return url;
    const driveMatch = url.match(/drive\.google\.com\/file\/d\/([^/]+)/);
    if (driveMatch) return `https://drive.google.com/file/d/${driveMatch[1]}/preview`;
    if (url.includes('dropbox.com')) return url.replace('?dl=0', '?raw=1');
    return url;
}

// === AUTENTICACIÓN ===
async function checkAuth(options = {}) {
    const { showAdmin = true, redirectOnFail = false } = options;
    try {
        const res = await fetch('/api/auth/me');
        if (!res.ok) {
            if (redirectOnFail) location.href = '/login';
            return null;
        }
        const user = await res.json();
        
        const authLinks = document.getElementById('authLinks');
        const userMenu = document.getElementById('userMenu');
        const userName = document.getElementById('userName');
        const adminLink = document.getElementById('adminLink');
        
        if (authLinks) authLinks.style.display = 'none';
        if (userMenu) {
            userMenu.style.display = 'flex';
            // Marcamos el menu del usuario para que el CSS aplique un
            // "card" distinto segun membresia (dorado vs opaco).
            userMenu.classList.toggle('user-menu--premium', !!user.isPremium);
            userMenu.classList.toggle('user-menu--free', !user.isPremium);
        }
        if (userName) {
            const isPremium = !!user.isPremium;
            // Corona (premium) o marcador gris (free)
            const leadingIcon = isPremium
                ? '<svg class="user-crown" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3l2.39 4.84L20 9l-4 3.89.94 5.48L12 15.77 7.06 18.37 8 12.89 4 9l5.61-1.16L12 3z"/><path d="M3 20h18v2H3z"/></svg>'
                : '<span class="user-dot" aria-hidden="true"></span>';
            const badgeClass = isPremium ? 'user-badge user-badge--premium' : 'user-badge user-badge--free';
            const badgeLabel = isPremium ? 'PREMIUM' : 'FREE';
            const badgeIcon = isPremium
                ? '<svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>'
                : '';
            // CTA solo para usuarios gratuitos: invita a suscribirse
            const cta = isPremium
                ? ''
                : ' <a href="/subscription" class="upgrade-cta" data-testid="upgrade-cta" title="Mejora a premium">' +
                  '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><polyline points="18 15 12 9 6 15"/></svg>' +
                  'Hazte Premium</a>';
            userName.innerHTML =
                leadingIcon +
                '<span class="user-name-text" data-testid="user-name-text">' +
                escapeHtml(user.name || '') +
                '</span>' +
                '<span class="' + badgeClass + '" data-testid="user-membership-badge" title="' +
                (isPremium ? 'Cuenta premium activa' : 'Cuenta gratuita. Actualiza a premium.') +
                '">' + badgeIcon + badgeLabel + '</span>' +
                cta;
        }
        if (adminLink && showAdmin && user.role === 'admin') {
            adminLink.style.display = 'inline';
        }
        
        return user;
    } catch (e) {
        if (redirectOnFail) location.href = '/login';
        return null;
    }
}

async function doLogout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    location.href = '/';
}

function setupLogout() {
    const btn = document.getElementById('logoutBtn');
    if (btn) {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            doLogout();
        });
    }
}

// === BOOK CARD ===
function renderBookCard(book) {
    const cover = convertDriveImageUrl(book.coverUrl) || PLACEHOLDER_IMG;
    return `
        <div class="book-card" onclick="location.href='/book/${book._id}'" data-testid="book-card-${book._id}">
            <img src="${cover}" alt="${escapeHtml(book.title)}" loading="lazy" onerror="this.src='${PLACEHOLDER_IMG}'">
            <div class="book-card-content">
                <h3>${escapeHtml(book.title)}</h3>
                <p>${escapeHtml(book.author)}</p>
            </div>
        </div>
    `;
}

// === PAYPAL ===
let paypalSdkLoaded = false;

async function loadPaypalSdk() {
    if (paypalSdkLoaded) return true;
    try {
        const cfg = await fetch('/api/paypal/config').then(r => r.json());
        if (!cfg.clientId) {
            alert('Falta configurar PAYPAL_CLIENT_ID en el servidor');
            return false;
        }
        const script = document.createElement('script');
        script.src = `https://www.paypal.com/sdk/js?client-id=${cfg.clientId}&currency=${cfg.currency || 'USD'}`;
        document.head.appendChild(script);
        await new Promise((resolve, reject) => {
            script.onload = resolve;
            script.onerror = reject;
        });
        paypalSdkLoaded = true;
        return true;
    } catch (e) {
        return false;
    }
}

async function renderPaypal() {
    const amount = Number(document.getElementById('donateAmount').value);
    if (!Number.isFinite(amount) || amount <= 0) {
        alert('Monto inválido');
        return;
    }
    if (!await loadPaypalSdk()) return;

    const container = document.getElementById('paypalButtons');
    container.innerHTML = '';

    window.paypal.Buttons({
        createOrder: async () => {
            const res = await fetch('/api/paypal/create-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'No se pudo crear la orden');
            return data.orderId;
        },
        onApprove: async (data) => {
            const res = await fetch(`/api/paypal/capture-order/${data.orderID}`, { method: 'POST' });
            if (!res.ok) throw new Error('No se pudo capturar');
            alert('¡Gracias por tu donación!');
            closeDonateModal();
        },
        onError: (err) => {
            console.error('PayPal error:', err);
            alert('Error con PayPal');
        }
    }).render('#paypalButtons');
}

// === MODAL DE DONACIÓN ===
function openDonateModal() {
    document.getElementById('donateModal').classList.add('active');
}

function closeDonateModal() {
    document.getElementById('donateModal').classList.remove('active');
}

function setAmount(val) {
    document.getElementById('donateAmount').value = val;
}

// Setup botón de donación
document.addEventListener('DOMContentLoaded', () => {
    const donateBtn = document.getElementById('donateBtn');
    if (donateBtn) {
        donateBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openDonateModal();
        });
    }
    
    // Cerrar modal con click fuera
    const modal = document.getElementById('donateModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeDonateModal();
        });
    }
});

// Inicializar auth y logout en todas las páginas
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupLogout();
});
