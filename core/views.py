"""Vistas de páginas (HTML) de la biblioteca.

Cada vista construye su propio contexto SEO mediante `core.seo.build_seo`
para que base.html renderice los meta tags, canonical, Open Graph,
Twitter Cards y JSON-LD sin perder funcionalidad ninguna.

La lógica de negocio sigue viviendo en `api/` (Mongo). Aquí solo leemos
MongoDB de forma read-only para enriquecer los metadatos de la ficha de
un libro.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from django.http import Http404
from django.shortcuts import render

from api.db import books_collection
from .seo import (
    build_seo,
    book_slug,
    jsonld_book,
    jsonld_breadcrumb,
    jsonld_organization,
    jsonld_website,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render(request, template: str, seo: Dict[str, Any], extra: Optional[Dict[str, Any]] = None):
    """Envuelve render() añadiendo el contexto SEO estándar."""
    context = {"seo": seo}
    if extra:
        context.update(extra)
    return render(request, template, context)


def _fetch_book_for_seo(book_id: str) -> Optional[Dict[str, Any]]:
    """Busca un libro en MongoDB solo para construir metadatos SEO.
    Devuelve None si el id no es válido o no existe. No afecta la API."""
    try:
        oid = ObjectId(book_id)
    except (InvalidId, TypeError, ValueError):
        return None
    try:
        projection = {
            "title": 1, "author": 1, "description": 1, "coverUrl": 1,
            "categories": 1, "isPremium": 1, "price": 1, "createdAt": 1,
        }
        book = books_collection().find_one({"_id": oid}, projection)
    except Exception:
        logger.warning("Error leyendo libro para SEO id=%s", book_id, exc_info=True)
        return None
    if not book:
        return None
    book["id"] = str(book.pop("_id"))
    return book


# ---------------------------------------------------------------------------
# Páginas públicas (indexables)
# ---------------------------------------------------------------------------

def index(request):
    """Home. Incluye JSON-LD de WebSite + Organization."""
    seo = build_seo(
        request,
        title=None,  # usa solo SITE_NAME como título
        description=(
            "Descubre miles de libros digitales: ficción, ciencia, historia, "
            "autoayuda y más. Lee gratis en línea o suscríbete para acceder "
            "a todo el contenido premium."
        ),
        path="/",
        og_type="website",
        keywords=["biblioteca virtual", "libros digitales", "lectura online",
                  "ebooks gratis", "libros premium"],
        jsonld=[jsonld_website(request), jsonld_organization(request)],
    )
    return _render(request, "index.html", seo)


def catalog(request):
    category = request.GET.get("category", "").strip()
    search = request.GET.get("search", "").strip()

    if category:
        title = f"Libros de {category}"
        desc = (
            f"Explora todos los libros de {category} en Biblioteca Virtual. "
            "Lee en línea, sin descargas ni complicaciones."
        )
    elif search:
        title = f'Resultados para "{search}"'
        desc = (
            f'Libros que coinciden con "{search}" en nuestra biblioteca digital.'
        )
    else:
        title = "Catálogo completo"
        desc = (
            "Navega el catálogo completo: más de mil libros digitales en "
            "múltiples categorías, con lectura en línea y descarga offline."
        )

    seo = build_seo(
        request,
        title=title,
        description=desc,
        og_type="website",
        keywords=["catálogo de libros", "libros online", category or "ebooks"],
        jsonld=[jsonld_breadcrumb(request, [
            {"name": "Inicio", "path": "/"},
            {"name": "Catálogo", "path": "/catalog"},
        ])],
    )
    return _render(request, "catalog.html", seo)


def book_detail(request, book_id: str, slug: str | None = None):
    """Ficha de un libro.
    Admite dos formatos de URL:
      /book/<id>                    (original, se mantiene intacto)
      /book/<slug>/<id>             (versión SEO-friendly)
    El ID siempre manda; el slug es puramente decorativo.
    """
    book = _fetch_book_for_seo(book_id)

    if book is None:
        # Mantenemos el comportamiento anterior: la vista sigue renderizando
        # book.html y es el JS quien muestra 'Libro no encontrado'. Así no
        # rompemos el flujo público. Devolvemos un SEO genérico con noindex.
        seo = build_seo(
            request,
            title="Libro",
            description="Ficha de libro en Biblioteca Virtual.",
            robots="noindex, follow",
        )
        return _render(request, "book.html", seo, {"book_id": book_id})

    title = f'{book["title"]} — {book.get("author") or "Autor desconocido"}'
    description = (
        book.get("description")
        or f'Lee {book["title"]} en Biblioteca Virtual.'
    )

    breadcrumb = [
        {"name": "Inicio", "path": "/"},
        {"name": "Catálogo", "path": "/catalog"},
        {"name": book["title"], "path": f"/book/{book['id']}"},
    ]

    canonical = f"/book/{book_slug(book)}/{book['id']}"

    seo = build_seo(
        request,
        title=title,
        description=description,
        path=canonical,
        canonical=canonical,
        image=book.get("coverUrl"),
        og_type="book",
        keywords=list(filter(None, [
            book.get("title"),
            book.get("author"),
            *(book.get("categories") or []),
        ])),
        jsonld=[jsonld_book(request, book), jsonld_breadcrumb(request, breadcrumb)],
    )
    return _render(request, "book.html", seo, {"book_id": book_id, "book": book})


def subscription_page(request):
    seo = build_seo(
        request,
        title="Suscripción Premium",
        description=(
            "Accede a todos los libros premium con una suscripción mensual o "
            "anual. Lectura ilimitada, sin anuncios y sincronización entre "
            "dispositivos."
        ),
        og_type="product",
        keywords=["suscripción premium", "libros ilimitados", "plan anual",
                  "plan mensual"],
        jsonld=[jsonld_breadcrumb(request, [
            {"name": "Inicio", "path": "/"},
            {"name": "Suscripción", "path": "/subscription"},
        ])],
    )
    return _render(request, "subscription.html", seo)


# ---------------------------------------------------------------------------
# Páginas privadas / transaccionales (noindex)
# ---------------------------------------------------------------------------

def _noindex_seo(request, title: str, description: str):
    return build_seo(
        request,
        title=title,
        description=description,
        robots="noindex, nofollow",
    )


def login_page(request):
    return _render(request, "login.html",
                   _noindex_seo(request, "Iniciar sesión", "Accede a tu cuenta."))


def register_page(request):
    return _render(request, "register.html",
                   _noindex_seo(request, "Crear cuenta", "Regístrate gratis."))


def forgot_password_page(request):
    return _render(
        request, "forgot_password.html",
        _noindex_seo(request, "Recuperar contraseña",
                     "Solicita un enlace para restablecer tu contraseña."),
    )


def reset_password_page(request):
    return _render(
        request, "reset_password.html",
        _noindex_seo(request, "Nueva contraseña",
                     "Define una nueva contraseña para tu cuenta."),
    )


def reader(request, book_id: str):
    return _render(
        request, "reader.html",
        _noindex_seo(request, "Lector", "Lector de libros online."),
        {"book_id": book_id},
    )


def dashboard(request):
    return _render(
        request, "dashboard.html",
        _noindex_seo(request, "Panel de administración",
                     "Administra libros, usuarios y categorías."),
    )


def my_library(request):
    return _render(
        request, "my_library.html",
        _noindex_seo(request, "Mi biblioteca",
                     "Tu progreso, favoritos e historial de lectura."),
    )


def verify_email_page(request):
    return _render(
        request, "verify_email.html",
        _noindex_seo(request, "Verificar email", "Verifica tu cuenta."),
    )


def google_callback_page(request):
    return _render(
        request, "google_callback.html",
        _noindex_seo(request, "Autenticación con Google",
                     "Procesando autenticación con Google."),
    )
