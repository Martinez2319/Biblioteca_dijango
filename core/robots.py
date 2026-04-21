"""
Vistas auxiliares para SEO:
  * /robots.txt – indica a los crawlers qué indexar y dónde está el sitemap.
  * / (index)   – delegada aquí para inyectar JSON-LD de WebSite/Organization.
"""

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import cache_control

from .seo import absolute_url


@cache_control(max_age=3600, public=True)
def robots_txt(request) -> HttpResponse:
    """robots.txt dinámico. Bloquea rutas privadas y enlaza el sitemap."""
    sitemap_url = absolute_url(request, "/sitemap.xml")
    lines = [
        "User-agent: *",
        "Allow: /",
        # Bloqueamos secciones privadas/transaccionales que no aportan a SEO
        "Disallow: /admin/",
        "Disallow: /api/",
        "Disallow: /dashboard",
        "Disallow: /my-library",
        "Disallow: /login",
        "Disallow: /register",
        "Disallow: /forgot-password",
        "Disallow: /reset-password",
        "Disallow: /verify-email",
        "Disallow: /reader/",
        "Disallow: /auth/",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
