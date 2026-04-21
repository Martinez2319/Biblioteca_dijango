# 📚 Biblioteca Virtual - ReadOn
> Una plataforma "Kindle-as-a-Service" de lectura digital (ebooks) en español, construida con una arquitectura híbrida de alto rendimiento.

![GitHub Streak](https://github-readme-streak-stats.herokuapp.com/?user=danielmartinez&theme=tokyonight&hide_border=true)
![Django](https://img.shields.io/badge/Django-4.2-092e20?style=for-the-badge&logo=django)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb)
![PayPal](https://img.shields.io/badge/PayPal-003087?style=for-the-badge&logo=paypal)

---

## 📖 Sobre el Proyecto
**Biblioteca Virtual** es una plataforma web completa diseñada para la lectura de libros digitales en línea. Inspirada en servicios como *Scribd* o *Wattpad*, ofrece una experiencia personalizada donde la gestión de datos masivos se maneja mediante **MongoDB Atlas**, mientras que la robustez administrativa y el SEO se gestionan con **Django**.

### 🚀 Características Principales
- **Experiencia de Lectura Pro:** Sistema de progreso, marcadores, subrayados (highlights) y notas personales.
- **Seguridad Avanzada:** Autenticación vía JWT (cookies httpOnly), cifrado Bcrypt e integración con Google OAuth.
- **Monetización Real:** Integración con el Sandbox de PayPal para suscripciones mensuales/anuales y donaciones.
- **Módulo Remoto (PC-Server):** Servidor auxiliar en Node.js que permite a los usuarios exponer sus propios archivos locales en la nube.
- **Optimización SEO:** Implementación de JSON-Ld, Sitemaps dinámicos y Open Graph para máxima visibilidad.

---

## 🏗️ Stack Técnico

| Capa | Tecnología |
| :--- | :--- |
| **Backend** | Django 4.2.30 + Django REST Framework 3.17 |
| **Base de Datos** | MongoDB Atlas (Colecciones) + SQLite (Sesiones/Admin) |
| **Autenticación** | JWT (PyJWT) + Google OAuth + Cookies Seguras |
| **Frontend** | Django Templates + HTML/CSS/JS Vanilla (SSR para SEO) |
| **Pagos** | PayPal SDK (Suscripciones y Órdenes) |
| **Mobile** | Preparado para empaquetado Android/iOS con Capacitor |

---

## 🗂️ Estructura del Código

```text
backend/
├── config/          # Configuración central (Settings, ASGI/WSGI)
├── core/            # Vistas públicas, SEO, sitemaps y processors
├── api/             # Lógica REST modularizada por dominios:
│   ├── views_auth.py       # Registro y seguridad JWT
│   ├── views_books.py      # CRUD y gestión de catálogo
│   ├── views_user_features.py # Progreso, favoritos e historial
│   ├── views_paypal.py     # Pasarela de pagos
│   └── db.py               # Cliente PyMongo y conexión a Atlas
├── templates/       # Vistas SSR (Reader, Dashboard, Library)
└── static/          # Recursos estáticos (CSS, JS, Imágenes)

pc-server/           # Servidor Express/Node para archivos locales
🛠️ Instalación y Configuración
Clonar el repositorio:

Bash
git clone [https://github.com/danielmartinez/biblioteca-virtual.git](https://github.com/danielmartinez/biblioteca-virtual.git)
cd biblioteca-virtual
Entorno Virtual:

Bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
Variables de Entorno (.env):
Configura tus credenciales para MongoDB Atlas, PayPal Client ID y SMTP de Gmail.

Ejecutar:

Bash
python manage.py runserver
🛠️ Módulo Auxiliar: PC-Server
Este proyecto incluye un servidor en /pc-server desarrollado en Express/Node.js. Su función es actuar como un puente para que el usuario pueda servir libros almacenados localmente en su PC directamente hacia la interfaz de la Biblioteca Virtual, sin necesidad de subirlos manualmente a la nube.

Desarrollado por Daniel Martinez - Estudiante de la Universidad Tecnológica de Ciudad Juárez (UTCJ).
