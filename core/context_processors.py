"""
Procesadores de contexto globales para templates.

Inyectan en cada render variables comunes (datos del sitio, valores por
defecto SEO y configuración de PayPal) evitando tener que pasarlos desde
cada vista.
"""

from django.conf import settings


def site_settings(request):
    """Expone configuración no sensible del sitio para los templates.

    Variables disponibles:
        SITE_NAME           – nombre mostrado
        SITE_URL            – URL canónica (sin trailing slash)
        DEFAULT_META_DESCRIPTION, DEFAULT_META_IMAGE
        PAYPAL_CLIENT_ID    – el `client-id` público para el SDK de PayPal
        PAYPAL_CURRENCY     – moneda configurada (USD por defecto)
    """
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Biblioteca Virtual"),
        "SITE_URL": getattr(settings, "SITE_URL", ""),
        "DEFAULT_META_DESCRIPTION": getattr(settings, "DEFAULT_META_DESCRIPTION", ""),
        "DEFAULT_META_IMAGE": getattr(settings, "DEFAULT_META_IMAGE", ""),
        "PAYPAL_CLIENT_ID": getattr(settings, "PAYPAL_CLIENT_ID", ""),
        "PAYPAL_CURRENCY": getattr(settings, "PAYPAL_CURRENCY", "USD"),
    }
