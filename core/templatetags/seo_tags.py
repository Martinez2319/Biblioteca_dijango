"""Filtros de plantilla para SEO.

Uso:
    {% load seo_tags %}
    <script type="application/ld+json">{{ data|jsonld_script|safe }}</script>
"""

from django import template

from core.seo import jsonld_to_script

register = template.Library()


@register.filter(name="jsonld_script")
def jsonld_script(data):
    """Serializa a JSON con escape seguro contra `</script>`."""
    return jsonld_to_script(data)
