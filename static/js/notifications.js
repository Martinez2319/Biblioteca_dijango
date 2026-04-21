/*
 * Sistema de notificaciones (campana del navbar).
 * Extraído de base.html para mantener el HTML limpio y permitir caching.
 * Se activa solo si el usuario está autenticado (llama a /api/auth/me).
 */
(function () {
    let notifications = [];

    function byId(id) { return document.getElementById(id); }

    function formatDate(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = (now - date) / 1000;
        if (diff < 60) return 'Hace un momento';
        if (diff < 3600) return `Hace ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} horas`;
        return date.toLocaleDateString();
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function updateUI() {
        const badge = byId('notificationBadge');
        const list = byId('notificationList');
        if (!list) return;

        const unreadCount = notifications.filter(n => !n.read).length;
        if (badge) {
            if (unreadCount > 0) {
                badge.textContent = unreadCount > 9 ? '9+' : String(unreadCount);
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }

        if (notifications.length === 0) {
            list.innerHTML = '<p class="no-notifications">No tienes notificaciones</p>';
        } else {
            list.innerHTML = notifications.map(n => `
                <div class="notification-item ${n.read ? '' : 'unread'}" data-id="${escapeHtml(n.id)}" data-link="${escapeHtml(n.link || '')}">
                    <h4>${escapeHtml(n.title)}</h4>
                    <p>${escapeHtml(n.message)}</p>
                    <p style="margin-top: 0.25rem; font-size: 0.6875rem;">${formatDate(n.createdAt)}</p>
                </div>
            `).join('');
        }
    }

    async function load() {
        try {
            const res = await fetch('/api/notifications');
            if (res.ok) {
                notifications = await res.json();
                updateUI();
            }
        } catch (e) {
            console.error('Error loading notifications:', e);
        }
    }

    async function openNotification(id, link) {
        try {
            await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
            notifications = notifications.map(n => n.id === id ? { ...n, read: true } : n);
            updateUI();
            if (link) location.href = link;
        } catch (e) {
            console.error('Error marking notification read:', e);
        }
    }

    async function markAllRead() {
        try {
            await fetch('/api/notifications/read-all', { method: 'POST' });
            notifications = notifications.map(n => ({ ...n, read: true }));
            updateUI();
        } catch (e) {
            console.error('Error marking all read:', e);
        }
    }

    // Exponemos markAllRead para el botón inline del template.
    window.markAllRead = markAllRead;

    document.addEventListener('DOMContentLoaded', () => {
        const btn = byId('notificationBtn');
        const panel = byId('notificationPanel');

        if (btn && panel) {
            btn.addEventListener('click', () => panel.classList.toggle('open'));
            document.addEventListener('click', (e) => {
                if (!panel.contains(e.target) && !btn.contains(e.target)) {
                    panel.classList.remove('open');
                }
            });
        }

        const list = byId('notificationList');
        if (list) {
            list.addEventListener('click', (e) => {
                const item = e.target.closest('.notification-item');
                if (!item) return;
                openNotification(item.dataset.id, item.dataset.link);
            });
        }

        // Activar notificaciones solo si hay sesión.
        fetch('/api/auth/me').then(res => {
            if (!res.ok) return;
            if (btn) btn.style.display = 'flex';
            load();
            setInterval(load, 60000);
        });
    });
})();
