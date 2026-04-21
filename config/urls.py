from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.cache import cache_page

from core.robots import robots_txt
from core.sitemaps import sitemaps as site_sitemaps

urlpatterns = [
    path('admin/', admin.site.urls),

    # SEO: robots y sitemap se sirven directamente desde Django.
    # Cacheamos el sitemap 1 hora para no golpear MongoDB en cada crawl.
    path('robots.txt', robots_txt, name='robots_txt'),
    path(
        'sitemap.xml',
        cache_page(60 * 60)(sitemap),
        {'sitemaps': site_sitemaps},
        name='django.contrib.sitemaps.views.sitemap',
    ),

    path('api/', include('api.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
