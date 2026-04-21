"""
Sitemaps dinámicos para SEO.

Exponemos 3 sitemaps accesibles desde `/sitemap.xml`:
  * static   – páginas con URL fija (home, catálogo, suscripción, etc.)
  * books    – un item por libro publicado (datos leídos de MongoDB)
  * categories – un item por categoría publicada

Los datos de libros y categorías se obtienen desde MongoDB sin tocar el ORM
(se hace lo mismo en el resto del proyecto). Si Mongo no está disponible, el
sitemap devuelve una lista vacía en lugar de romper la petición.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from api.db import books_collection, categories_collection

logger = logging.getLogger(__name__)


class StaticViewSitemap(Sitemap):
    """Páginas estáticas: siempre indexables."""
    priority = 0.8
    changefreq = "weekly"
    protocol = "https"

    def items(self) -> List[str]:
        return ["index", "catalog", "subscription"]

    def location(self, item: str) -> str:
        return reverse(item)


class BookSitemap(Sitemap):
    """Un entry por libro publicado."""
    priority = 0.7
    changefreq = "weekly"
    protocol = "https"
    limit = 5000

    def items(self) -> List[Dict[str, Any]]:
        try:
            projection = {"_id": 1, "title": 1, "author": 1,
                          "createdAt": 1, "updatedAt": 1}
            return list(books_collection().find({}, projection))
        except Exception:
            logger.warning("No se pudo construir sitemap de libros", exc_info=True)
            return []

    def location(self, item: Dict[str, Any]) -> str:
        return f"/book/{item['_id']}"

    def lastmod(self, item: Dict[str, Any]):
        return item.get("updatedAt") or item.get("createdAt")


class CategorySitemap(Sitemap):
    """Landing de catálogo por categoría (query `?category=`)."""
    priority = 0.5
    changefreq = "weekly"
    protocol = "https"

    def items(self) -> List[Dict[str, Any]]:
        try:
            projection = {"_id": 1, "name": 1, "slug": 1, "createdAt": 1}
            return list(categories_collection().find({}, projection))
        except Exception:
            logger.warning("No se pudo construir sitemap de categorías", exc_info=True)
            return []

    def location(self, item: Dict[str, Any]) -> str:
        # Reutilizamos la vista de catálogo con el filtro category (el frontend
        # ya sabe leer ese query param).
        from urllib.parse import quote
        return f"/catalog?category={quote(item.get('name') or '')}"

    def lastmod(self, item: Dict[str, Any]):
        return item.get("createdAt")


# Mapa que consume django.contrib.sitemaps.views.sitemap
sitemaps = {
    "static": StaticViewSitemap,
    "books": BookSitemap,
    "categories": CategorySitemap,
}
