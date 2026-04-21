"""
Helpers SEO para la biblioteca virtual.

Encapsulan la construcción del contexto SEO que se inyecta en cada template
(título, descripción, canonical, Open Graph, Twitter Cards y JSON-LD). Las
vistas no tienen que saber los detalles del HTML, solo llaman a estas
funciones y pasan el resultado al contexto.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify

# ---------------------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(text: str) -> str:
    """Elimina etiquetas HTML y colapsa espacios. Úsalo antes de meter texto
    de usuario en un meta tag."""
    if not text:
        return ""
    return _WS_RE.sub(" ", _HTML_TAG_RE.sub("", str(text))).strip()


def truncate(text: str, length: int = 160) -> str:
    """Recorta texto respetando palabras para meta description."""
    text = strip_html(text)
    if len(text) <= length:
        return text
    cut = text[: length - 1].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:!?") + "…"


def absolute_url(request, path: str) -> str:
    """Construye una URL absoluta robusta:
    - Si `path` ya es absoluta la devolvemos tal cual.
    - Si el path usa el prefijo interno `remote:<fichero>`, lo traducimos a la
      ruta pública servida por la API (`/api/remote/file/cover/<fichero>`).
      Esto es imprescindible para og:image / twitter:image / Schema.org image,
      porque los crawlers externos no entienden el prefijo interno.
    - Si tenemos `request`, usamos `build_absolute_uri`.
    - En su defecto, caemos en `settings.SITE_URL`.
    """
    if not path:
        return ""
    if path.startswith("remote:"):
        # El prefijo es usado por el pipeline PC-server para servir portadas
        # desde un disco local. Para SEO lo convertimos en la URL HTTP pública.
        filename = path[len("remote:"):]
        path = f"/api/remote/file/cover/{filename}"
    if path.startswith(("http://", "https://")):
        return path
    if request is not None:
        try:
            return request.build_absolute_uri(path)
        except Exception:  # pragma: no cover - fallback defensivo
            pass
    base = getattr(settings, "SITE_URL", "").rstrip("/")
    return f"{base}{path if path.startswith('/') else '/' + path}"


# ---------------------------------------------------------------------------
# Construcción del contexto SEO
# ---------------------------------------------------------------------------

def build_seo(
    request,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    path: Optional[str] = None,
    image: Optional[str] = None,
    og_type: str = "website",
    keywords: Optional[List[str]] = None,
    robots: Optional[str] = None,
    canonical: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    jsonld: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Devuelve un diccionario SEO listo para pasar al template.

    Campos devueltos (todos con valores por defecto sensatos):
        meta_title, meta_description, meta_keywords, meta_robots,
        meta_image, canonical_url, og_type, jsonld (lista)
    """
    site_name = getattr(settings, "SITE_NAME", "Biblioteca Virtual")
    default_desc = getattr(
        settings,
        "DEFAULT_META_DESCRIPTION",
        "Lee libros digitales gratis y premium. Explora ficción, ciencia, "
        "historia y más en Biblioteca Virtual.",
    )
    default_image = getattr(settings, "DEFAULT_META_IMAGE", "")

    # Título: si el llamador no pasó uno, usamos el nombre del sitio solo.
    # Si sí pasa uno, usamos un formato "Título | Biblioteca Virtual" salvo
    # que ya contenga el nombre del sitio.
    if title:
        if site_name and site_name.lower() in title.lower():
            final_title = title
        else:
            final_title = f"{title} | {site_name}"
    else:
        final_title = site_name

    final_description = truncate(description or default_desc, 160)

    # Canonical: si no nos dan uno, usamos la ruta actual de la petición.
    if canonical is None:
        if path is not None:
            canonical = absolute_url(request, path)
        elif request is not None:
            canonical = absolute_url(request, request.path)
        else:
            canonical = ""
    elif canonical and not canonical.startswith(("http://", "https://")):
        canonical = absolute_url(request, canonical)

    # Imagen Open Graph: permitimos absoluta o relativa.
    if image:
        meta_image = absolute_url(request, image)
    elif default_image:
        meta_image = absolute_url(request, default_image)
    else:
        meta_image = ""

    ctx: Dict[str, Any] = {
        "meta_title": final_title,
        "meta_description": final_description,
        "meta_keywords": ", ".join(keywords) if keywords else "",
        "meta_robots": robots or "index, follow",
        "meta_image": meta_image,
        "canonical_url": canonical,
        "og_type": og_type,
        "jsonld": jsonld or [],
    }
    if extra:
        ctx.update(extra)
    return ctx


# ---------------------------------------------------------------------------
# JSON-LD builders
# ---------------------------------------------------------------------------

def jsonld_website(request) -> Dict[str, Any]:
    """Schema WebSite con SearchAction (muestra caja de búsqueda en Google)."""
    site_url = absolute_url(request, "/")
    # Construimos la plantilla sin pasar por URL-encoding; Google necesita las
    # llaves literales `{search_term_string}`.
    search_url = f"{site_url.rstrip('/')}/catalog?search={{search_term_string}}"
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": getattr(settings, "SITE_NAME", "Biblioteca Virtual"),
        "url": site_url,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": search_url,
            },
            "query-input": "required name=search_term_string",
        },
    }


def jsonld_organization(request) -> Dict[str, Any]:
    site_url = absolute_url(request, "/")
    logo = getattr(settings, "DEFAULT_META_IMAGE", "")
    data = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": getattr(settings, "SITE_NAME", "Biblioteca Virtual"),
        "url": site_url,
    }
    if logo:
        data["logo"] = absolute_url(request, logo)
    return data


def jsonld_book(request, book: Dict[str, Any]) -> Dict[str, Any]:
    """Schema.org Book para la ficha de un libro."""
    book_id = str(book.get("id") or book.get("_id") or "")
    url = absolute_url(request, f"/book/{book_id}")
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Book",
        "name": book.get("title") or "Libro",
        "author": {"@type": "Person", "name": book.get("author") or "Desconocido"},
        "url": url,
    }
    if book.get("description"):
        data["description"] = truncate(book["description"], 300)
    if book.get("coverUrl"):
        data["image"] = absolute_url(request, book["coverUrl"])
    cats = book.get("categories") or []
    if cats:
        data["genre"] = cats if len(cats) > 1 else cats[0]
    rating = book.get("averageRating") or 0
    reviews = book.get("totalReviews") or 0
    if rating and reviews:
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": rating,
            "reviewCount": reviews,
            "bestRating": 5,
            "worstRating": 1,
        }
    # Oferta solo para libros premium con precio > 0
    if book.get("isPremium") and book.get("price"):
        data["offers"] = {
            "@type": "Offer",
            "price": f"{float(book['price']):.2f}",
            "priceCurrency": getattr(settings, "PAYPAL_CURRENCY", "USD"),
            "availability": "https://schema.org/InStock",
            "url": url,
        }
    return data


def jsonld_breadcrumb(request, items: List[Dict[str, str]]) -> Dict[str, Any]:
    """items = [{'name': 'Inicio', 'path': '/'}, ...]"""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": idx + 1,
                "name": it["name"],
                "item": absolute_url(request, it["path"]),
            }
            for idx, it in enumerate(items)
        ],
    }


def jsonld_to_script(data: Any) -> str:
    """Serializa a JSON escapando '</' para evitar cerrar el <script>."""
    return json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")


# ---------------------------------------------------------------------------
# Slugs SEO-friendly para libros
# ---------------------------------------------------------------------------

def book_slug(book: Dict[str, Any]) -> str:
    """Genera un slug legible para un libro ('titulo-autor') útil en URLs
    amigables. Nunca depende del slug para resolver el libro (se resuelve por
    _id); existe solo por SEO."""
    base = " ".join(filter(None, [book.get("title"), book.get("author")]))
    s = slugify(base)
    return s[:80] if s else "libro"
