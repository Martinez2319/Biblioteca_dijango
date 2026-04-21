const express = require('express');
const cors = require('cors');
const compression = require('compression');
const axios = require('axios');
const path = require('path');
const fs = require('fs');

// Configuración
let config;
try {
    config = require('./config.json');
} catch (e) {
    console.error('❌ No se encontró config.json');
    console.log('📝 Crea config.json con la siguiente estructura:');
    console.log(JSON.stringify({
        serverUrl: "https://tu-servidor.com",
        apiKey: "TU_API_KEY",
        booksFolder: "/home/alexisesponda/MisLibros",
        localPort: 3001,
        pcName: "Mi PC"
    }, null, 2));
    process.exit(1);
}

const app = express();

// === MIDDLEWARE ===
app.use(cors());
app.use(express.json());

// Compresión GZIP para respuestas (mejora ~60-70% en tamaño)
app.use(compression({
    level: 6,
    threshold: 1024, // Solo comprimir respuestas > 1KB
    filter: (req, res) => {
        // No comprimir PDFs (ya están comprimidos internamente)
        if (req.path.includes('/file/pdf/')) {
            return false;
        }
        return compression.filter(req, res);
    }
}));

// === CONFIGURACIÓN DE CARPETAS ===
const BOOKS_FOLDER = config.booksFolder || 'C:\\MisLibros';
const PDF_FOLDER = path.join(BOOKS_FOLDER, 'pdfs');
const COVERS_FOLDER = path.join(BOOKS_FOLDER, 'covers');

// Crear carpetas si no existen
[PDF_FOLDER, COVERS_FOLDER].forEach(folder => {
    if (!fs.existsSync(folder)) {
        fs.mkdirSync(folder, { recursive: true });
        console.log(`📁 Carpeta creada: ${folder}`);
    }
});

// === HELPERS ===

// Verificar API Key
const verifyKey = (req, res, next) => {
    const key = req.headers['x-api-key'] || req.query.apiKey;
    if (key !== config.apiKey) {
        return res.status(401).json({ error: 'API key inválida' });
    }
    next();
};

// Listar archivos de carpeta
const listFiles = (folder, extensions) => {
    if (!fs.existsSync(folder)) return [];
    return fs.readdirSync(folder)
        .filter(f => extensions.some(ext => f.toLowerCase().endsWith(ext)))
        .map(f => {
            const stats = fs.statSync(path.join(folder, f));
            return { 
                name: f, 
                size: stats.size,
                modified: stats.mtime.toISOString()
            };
        });
};

// Determinar MIME type
const getMimeType = (filename) => {
    const ext = path.extname(filename).toLowerCase();
    const mimeTypes = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif'
    };
    return mimeTypes[ext] || 'application/octet-stream';
};

// === ENDPOINTS ===

// Health check
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        name: config.pcName || 'PC Server',
        version: '2.0.0',
        time: new Date().toISOString(),
        features: ['streaming', 'gzip', 'range-requests']
    });
});

// Listar archivos
app.get('/files', verifyKey, (req, res) => {
    try {
        res.json({
            pdfs: listFiles(PDF_FOLDER, ['.pdf']),
            covers: listFiles(COVERS_FOLDER, ['.jpg', '.png', '.jpeg', '.webp', '.gif']),
            booksFolder: BOOKS_FOLDER
        });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// === STREAMING OPTIMIZADO PARA PDFs ===
app.get('/file/pdf/:filename', verifyKey, (req, res) => {
    try {
        const filename = req.params.filename;
        const filepath = path.join(PDF_FOLDER, filename);
        
        // Validar path traversal
        if (!filepath.startsWith(PDF_FOLDER)) {
            return res.status(403).json({ error: 'Acceso denegado' });
        }
        
        if (!fs.existsSync(filepath)) {
            return res.status(404).json({ error: 'Archivo no encontrado' });
        }

        const stat = fs.statSync(filepath);
        const fileSize = stat.size;
        const range = req.headers.range;

        // Soporte para Range Requests (streaming progresivo)
        if (range) {
            const parts = range.replace(/bytes=/, '').split('-');
            const start = parseInt(parts[0], 10);
            const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
            const chunkSize = (end - start) + 1;

            res.writeHead(206, {
                'Content-Range': `bytes ${start}-${end}/${fileSize}`,
                'Accept-Ranges': 'bytes',
                'Content-Length': chunkSize,
                'Content-Type': 'application/pdf',
                'Cache-Control': 'public, max-age=86400'
            });

            const stream = fs.createReadStream(filepath, { start, end });
            stream.pipe(res);
        } else {
            // Sin range: enviar archivo completo con streaming
            res.writeHead(200, {
                'Content-Length': fileSize,
                'Content-Type': 'application/pdf',
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'public, max-age=86400'
            });

            // Usar chunks de 64KB para mejor rendimiento
            const stream = fs.createReadStream(filepath, { highWaterMark: 65536 });
            stream.pipe(res);
        }

    } catch (e) {
        console.error('Error sirviendo PDF:', e);
        res.status(500).json({ error: 'Error al leer archivo' });
    }
});

// === STREAMING PARA IMÁGENES ===
app.get('/file/cover/:filename', verifyKey, (req, res) => {
    try {
        const filename = req.params.filename;
        const filepath = path.join(COVERS_FOLDER, filename);
        
        // Validar path traversal
        if (!filepath.startsWith(COVERS_FOLDER)) {
            return res.status(403).json({ error: 'Acceso denegado' });
        }
        
        if (!fs.existsSync(filepath)) {
            return res.status(404).json({ error: 'Archivo no encontrado' });
        }

        const stat = fs.statSync(filepath);
        const mimeType = getMimeType(filename);

        res.writeHead(200, {
            'Content-Length': stat.size,
            'Content-Type': mimeType,
            'Cache-Control': 'public, max-age=604800', // 1 semana para imágenes
            'ETag': `"${stat.size}-${stat.mtime.getTime()}"`
        });

        // Stream con chunks de 32KB para imágenes
        const stream = fs.createReadStream(filepath, { highWaterMark: 32768 });
        stream.pipe(res);

    } catch (e) {
        console.error('Error sirviendo imagen:', e);
        res.status(500).json({ error: 'Error al leer archivo' });
    }
});

// === COMUNICACIÓN CON SERVIDOR PRINCIPAL ===
const apiCall = async (endpoint, method = 'post', data = {}) => {
    try {
        const response = await axios({
            method,
            url: `${config.serverUrl}/api/remote/${endpoint}`,
            data,
            headers: { 'X-Api-Key': config.apiKey },
            timeout: method === 'post' ? 10000 : 5000
        });
        return response.data;
    } catch (e) {
        console.error(`Error en ${endpoint}:`, e.message);
        return null;
    }
};

const register = async (url) => {
    const res = await apiCall('register', 'post', { 
        url, 
        name: config.pcName || 'Mi PC' 
    });
    if (res?.success) {
        console.log('✅ Registrado con el servidor principal');
        return true;
    }
    console.log('⚠️ No se pudo registrar con el servidor');
    return false;
};

// === INICIAR SERVIDOR ===
const PORT = config.localPort || 3001;
const publicUrl = process.env.TUNNEL_URL;

app.listen(PORT, async () => {
    console.log('\n╔════════════════════════════════════════════╗');
    console.log('║  📚 PC SERVER v2.0 - BIBLIOTECA VIRTUAL   ║');
    console.log('║     Streaming + GZIP Optimization          ║');
    console.log('╠════════════════════════════════════════════╣');
    console.log(`║  📁 Carpeta: ${BOOKS_FOLDER.padEnd(29)}║`);
    console.log(`║  🖥️  Local: http://localhost:${PORT}`.padEnd(46) + '║');
    
    if (publicUrl) {
        console.log(`║  🌐 Público: ${publicUrl.substring(0, 28).padEnd(29)}║`);
        if (await register(publicUrl)) {
            // Heartbeat cada 30 segundos
            setInterval(() => apiCall('heartbeat'), 30000);
            console.log('║  💓 Heartbeat activo (30s)'.padEnd(45) + '║');
        }
    }
    
    console.log('╠════════════════════════════════════════════╣');
    console.log('║  ✅ Servidor corriendo                     ║');
    console.log('║     Presiona Ctrl+C para detener           ║');
    console.log('╚════════════════════════════════════════════╝\n');
});

// Cerrar limpio
const cleanup = async () => {
    console.log('\n🔌 Desconectando...');
    await apiCall('disconnect');
    console.log('👋 Hasta luego!\n');
    process.exit(0);
};

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);
