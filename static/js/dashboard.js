/**
 * Biblioteca Virtual - Dashboard Admin
 */

let allCategories = [];

// Init: verificar que sea admin
async function initAuth() {
    const user = await checkAuth({ redirectOnFail: true });
    if (!user || user.role !== 'admin') {
        location.href = '/';
        return false;
    }
    return true;
}

// Stats
async function loadStats() {
    try {
        const stats = await fetch('/api/stats').then(r => r.json());
        document.getElementById('totalBooks').textContent = stats.totalBooks;
        document.getElementById('totalUsers').textContent = stats.totalUsers;
        document.getElementById('totalCategories').textContent = stats.totalCategories;
    } catch (e) {
        console.error('Error loading stats:', e);
    }
}

// Tabs
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`${tab.dataset.tab}-tab`).classList.add('active');
    });
});

// === LIBROS ===
async function loadBooks() {
    try {
        const books = await fetch('/api/books').then(r => r.json());
        document.getElementById('booksTable').innerHTML = books.map(b => {
            const formato = b.pdfUrl && b.content 
                ? '<span class="format-badge"><span class="badge">PDF</span><span class="badge">Texto</span></span>' 
                : b.pdfUrl 
                    ? '<span class="badge">PDF</span>' 
                    : b.content 
                        ? '<span class="badge">Texto</span>' 
                        : '—';
            const premiumBadge = b.isPremium 
                ? `<span class="badge" style="background: linear-gradient(135deg, #f59e0b, #d97706); color: white;">💎 $${b.price || 0}</span>` 
                : '';
            return `<tr>
                <td>${escapeHtml(b.title)} ${premiumBadge}</td>
                <td>${escapeHtml(b.author)}</td>
                <td>${formato}</td>
                <td>${b.views || 0}</td>
                <td>
                    <div class="action-btns">
                        <button class="btn-icon-sm" onclick="editBook('${b._id}')" title="Editar">✏️</button>
                        <button class="btn-icon-sm danger" onclick="deleteBook('${b._id}')" title="Eliminar">🗑️</button>
                    </div>
                </td>
            </tr>`;
        }).join('');
    } catch (e) {
        console.error('Error loading books:', e);
    }
}

function openBookModal(book = null) {
    document.getElementById('bookModal').classList.add('active');
    document.getElementById('bookModalTitle').textContent = book ? 'Editar Libro' : 'Nuevo Libro';
    document.getElementById('bookId').value = book?._id || '';
    document.getElementById('bookTitle').value = book?.title || '';
    document.getElementById('bookAuthor').value = book?.author || '';
    document.getElementById('bookDesc').value = book?.description || '';
    document.getElementById('bookCategories').value = (book?.categories || []).join(', ');
    document.getElementById('bookCover').value = book?.coverUrl || '';
    document.getElementById('bookPdf').value = book?.pdfUrl || '';
    document.getElementById('bookContent').value = book?.content || '';
    document.getElementById('bookIsPremium').checked = book?.isPremium || false;
    document.getElementById('bookPrice').value = book?.price || '';
    togglePremiumPrice();
}

function togglePremiumPrice() {
    const isPremium = document.getElementById('bookIsPremium').checked;
    document.getElementById('priceGroup').style.display = isPremium ? 'block' : 'none';
    if (isPremium && !document.getElementById('bookPrice').value) {
        document.getElementById('bookPrice').value = '9.99';
    }
}

function closeBookModal() {
    document.getElementById('bookModal').classList.remove('active');
}

async function editBook(id) {
    try {
        const book = await fetch(`/api/books/${id}`).then(r => r.json());
        openBookModal(book);
    } catch (e) {
        console.error('Error loading book:', e);
    }
}

async function deleteBook(id) {
    if (!confirm('¿Eliminar este libro?')) return;
    try {
        await fetch(`/api/books/${id}/delete`, { method: 'DELETE' });
        loadBooks();
        loadStats();
    } catch (e) {
        console.error('Error deleting book:', e);
    }
}

document.getElementById('bookForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('bookId').value;
    const isPremium = document.getElementById('bookIsPremium').checked;
    const data = {
        title: document.getElementById('bookTitle').value,
        author: document.getElementById('bookAuthor').value,
        description: document.getElementById('bookDesc').value,
        categories: document.getElementById('bookCategories').value.split(',').map(c => c.trim()).filter(Boolean),
        coverUrl: document.getElementById('bookCover').value,
        pdfUrl: document.getElementById('bookPdf').value,
        content: document.getElementById('bookContent').value,
        isPremium: isPremium,
        price: isPremium ? parseFloat(document.getElementById('bookPrice').value) || 0 : 0
    };
    
    try {
        const url = id ? `/api/books/${id}/update` : `/api/books/new/create`;
        await fetch(url, {
            method: id ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        closeBookModal();
        loadBooks();
        loadStats();
    } catch (e) {
        console.error('Error saving book:', e);
    }
});

// === CATEGORÍAS ===
async function loadCategories() {
    try {
        const cats = await fetch('/api/categories').then(r => r.json());
        allCategories = cats;
        document.getElementById('categoriesTable').innerHTML = cats.map(c => `<tr>
            <td>${escapeHtml(c.name)}</td>
            <td><code>${escapeHtml(c.slug)}</code></td>
            <td>
                <div class="action-btns">
                    <button class="btn-icon-sm" onclick="editCategory('${c._id}')" title="Editar">✏️</button>
                    <button class="btn-icon-sm danger" onclick="deleteCategory('${c._id}')" title="Eliminar">🗑️</button>
                </div>
            </td>
        </tr>`).join('');
    } catch (e) {
        console.error('Error loading categories:', e);
    }
}

function openCategoryModal(cat = null) {
    document.getElementById('categoryModal').classList.add('active');
    document.getElementById('categoryModalTitle').textContent = cat ? 'Editar Categoría' : 'Nueva Categoría';
    document.getElementById('categoryId').value = cat?._id || '';
    document.getElementById('categoryName').value = cat?.name || '';
    document.getElementById('categorySlug').value = cat?.slug || '';
    document.getElementById('categoryDesc').value = cat?.description || '';
}

function closeCategoryModal() {
    document.getElementById('categoryModal').classList.remove('active');
}

function editCategory(id) {
    const cat = allCategories.find(c => c._id === id);
    if (cat) openCategoryModal(cat);
}

async function deleteCategory(id) {
    if (!confirm('¿Eliminar esta categoría?')) return;
    try {
        await fetch(`/api/categories/${id}/delete`, { method: 'DELETE' });
        loadCategories();
        loadStats();
    } catch (e) {
        console.error('Error deleting category:', e);
    }
}

document.getElementById('categoryForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('categoryId').value;
    const data = {
        name: document.getElementById('categoryName').value,
        slug: document.getElementById('categorySlug').value,
        description: document.getElementById('categoryDesc').value
    };
    
    try {
        const url = id ? `/api/categories/${id}/update` : `/api/categories/create`;
        await fetch(url, {
            method: id ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        closeCategoryModal();
        loadCategories();
        loadStats();
    } catch (e) {
        console.error('Error saving category:', e);
    }
});

document.getElementById('categoryName').addEventListener('input', (e) => {
    document.getElementById('categorySlug').value = e.target.value
        .toLowerCase()
        .replace(/\s+/g, '-')
        .replace(/[^a-z0-9-]/g, '');
});

// === USUARIOS ===
async function loadUsers() {
    try {
        const users = await fetch('/api/users').then(r => r.json());
        document.getElementById('usersTable').innerHTML = users.map(u => `<tr>
            <td>${escapeHtml(u.name)}</td>
            <td>${escapeHtml(u.email)}</td>
            <td>
                <select onchange="updateRole('${u._id}', this.value)" style="padding: 0.375rem; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-secondary); color: var(--text-primary);">
                    <option value="user" ${u.role === 'user' ? 'selected' : ''}>Usuario</option>
                    <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
            </td>
            <td>
                <button class="btn-icon-sm danger" onclick="deleteUser('${u._id}')" title="Eliminar">🗑️</button>
            </td>
        </tr>`).join('');
    } catch (e) {
        console.error('Error loading users:', e);
    }
}

async function updateRole(id, role) {
    try {
        await fetch(`/api/users/${id}/update`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role })
        });
    } catch (e) {
        console.error('Error updating role:', e);
    }
}

async function deleteUser(id) {
    if (!confirm('¿Eliminar este usuario?')) return;
    try {
        await fetch(`/api/users/${id}/delete`, { method: 'DELETE' });
        loadUsers();
        loadStats();
    } catch (e) {
        console.error('Error deleting user:', e);
    }
}

// === PC REMOTO ===
async function loadRemoteStatus() {
    const statusEl = document.getElementById('remoteStatusInfo');
    const filesEl = document.getElementById('remoteFilesInfo');
    const pcStatusValue = document.getElementById('pcStatusValue');
    const pcStatusCard = document.getElementById('pcStatusCard');

    try {
        const data = await fetch('/api/remote/status').then(r => r.json());

        if (!data.connected && data.message === 'No hay PC configurado') {
            pcStatusValue.textContent = 'Sin config';
            statusEl.innerHTML = `
                <p style="color: var(--text-muted);">No hay PC configurado.</p>
                <p style="margin-top: 0.5rem; font-size: 0.875rem;">Ejecuta <code>iniciar.bat</code> en tu PC desde la carpeta <code>pc-server</code></p>`;
            return;
        }

        if (data.connected) {
            pcStatusValue.textContent = 'Online';
            statusEl.innerHTML = `
                <p><strong>Nombre:</strong> ${escapeHtml(data.name)}</p>
                <p><strong>Estado:</strong> <span class="status-badge online">🟢 Conectado</span></p>
                <p><strong>Última conexión:</strong> ${new Date(data.lastSeen).toLocaleString()}</p>`;
            loadRemoteFiles();
        } else {
            pcStatusValue.textContent = 'Offline';
            statusEl.innerHTML = `
                <p><strong>Nombre:</strong> ${escapeHtml(data.name)}</p>
                <p><strong>Estado:</strong> <span class="status-badge offline">🔴 Desconectado</span></p>
                <p><strong>Última conexión:</strong> ${data.lastSeen ? new Date(data.lastSeen).toLocaleString() : 'Nunca'}</p>`;
            filesEl.innerHTML = '<p style="color: var(--text-muted);">El PC debe estar conectado para ver los archivos.</p>';
        }
    } catch (e) {
        pcStatusValue.textContent = 'Error';
        statusEl.innerHTML = '<p style="color: var(--danger);">Error al verificar estado</p>';
    }
}

async function loadRemoteFiles() {
    const filesEl = document.getElementById('remoteFilesInfo');
    try {
        const res = await fetch('/api/remote/files');
        if (!res.ok) {
            filesEl.innerHTML = '<p style="color: var(--text-muted);">No se pudo conectar con el PC.</p>';
            return;
        }
        const data = await res.json();
        let html = '';

        if (data.pdfs?.length) {
            html += '<h4 style="margin: 0.75rem 0 0.5rem; font-size: 0.9375rem;">📄 PDFs:</h4><ul style="list-style: none; font-size: 0.875rem;">';
            data.pdfs.forEach(f => {
                html += `<li style="padding: 0.25rem 0;"><code>remote:${escapeHtml(f.name)}</code> <span style="color: var(--text-muted);">(${(f.size/1024/1024).toFixed(2)} MB)</span></li>`;
            });
            html += '</ul>';
        }

        if (data.covers?.length) {
            html += '<h4 style="margin: 0.75rem 0 0.5rem; font-size: 0.9375rem;">🖼️ Portadas:</h4><ul style="list-style: none; font-size: 0.875rem;">';
            data.covers.forEach(f => {
                html += `<li style="padding: 0.25rem 0;"><code>remote:${escapeHtml(f.name)}</code> <span style="color: var(--text-muted);">(${(f.size/1024).toFixed(0)} KB)</span></li>`;
            });
            html += '</ul>';
        }

        if (!data.pdfs?.length && !data.covers?.length) {
            html = '<p style="color: var(--text-muted);">No hay archivos disponibles.</p>';
        }

        filesEl.innerHTML = html;
    } catch (e) {
        filesEl.innerHTML = '<p style="color: var(--danger);">Error cargando archivos</p>';
    }
}

// === INIT ===
async function init() {
    if (!await initAuth()) return;
    loadStats();
    loadBooks();
    loadCategories();
    loadUsers();
    loadRemoteStatus();
}

init();

