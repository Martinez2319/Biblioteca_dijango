"""Pruebas de regresión para el paquete SEO.

Objetivo: garantizar que la refactorización + SEO no rompen las páginas
existentes y que los endpoints de SEO (sitemap, robots.txt) funcionan
correctamente. No se tocan MongoDB ni la API de datos.
"""

from django.test import TestCase, Client


class SmokePagesTests(TestCase):
    """Las páginas HTML deben seguir cargando (no 5xx) tras el refactor."""

    PUBLIC_PAGES = [
        "/",
        "/catalog",
        "/login",
        "/register",
        "/forgot-password",
        "/reset-password",
        "/verify-email",
        "/subscription",
        "/my-library",
        "/dashboard",
        "/auth/google/callback",
    ]

    def test_public_pages_return_200(self):
        c = Client()
        for url in self.PUBLIC_PAGES:
            with self.subTest(url=url):
                resp = c.get(url)
                self.assertEqual(resp.status_code, 200, f"Falló {url}")

    def test_book_invalid_id_still_renders(self):
        # El comportamiento original era renderizar siempre book.html y dejar
        # al frontend mostrar 'Libro no encontrado'. Lo preservamos.
        resp = Client().get("/book/no-existe")
        self.assertEqual(resp.status_code, 200)

    def test_book_slug_url_backwards_compatible(self):
        # Acepta la URL original y la nueva con slug
        resp = Client().get("/book/abcdefabcdefabcdefabcdef")
        self.assertEqual(resp.status_code, 200)
        resp = Client().get("/book/mi-libro/abcdefabcdefabcdefabcdef")
        self.assertEqual(resp.status_code, 200)


class SeoMetaTests(TestCase):
    """Verifica que cada página renderiza las meta tags básicas."""

    def test_home_has_canonical_and_og(self):
        html = Client().get("/").content.decode()
        self.assertIn('<link rel="canonical"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:type"', html)
        self.assertIn('name="twitter:card"', html)
        # JSON-LD WebSite
        self.assertIn('"@type": "WebSite"', html)
        self.assertIn('"@type": "Organization"', html)

    def test_private_pages_are_noindex(self):
        for url in ["/login", "/register", "/dashboard", "/my-library",
                    "/forgot-password", "/reset-password", "/verify-email"]:
            with self.subTest(url=url):
                html = Client().get(url).content.decode()
                self.assertIn("noindex", html, f"{url} debería ser noindex")

    def test_catalog_with_category_has_specific_title(self):
        html = Client().get("/catalog?category=Ficcion").content.decode()
        self.assertIn("Libros de Ficcion", html)


class RobotsAndSitemapTests(TestCase):
    def test_robots_txt(self):
        resp = Client().get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp["Content-Type"])
        body = resp.content.decode()
        self.assertIn("User-agent: *", body)
        self.assertIn("Sitemap:", body)
        self.assertIn("Disallow: /admin/", body)
        self.assertIn("Disallow: /api/", body)

    def test_sitemap_xml(self):
        resp = Client().get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn("<urlset", body)
        # Al menos las 3 páginas estáticas
        self.assertIn("/catalog", body)
        self.assertIn("/subscription", body)


class SeoHelpersTests(TestCase):
    """Pruebas unitarias de los helpers que no dependen del ORM."""

    def test_truncate(self):
        from core.seo import truncate
        self.assertEqual(truncate("hola mundo", 100), "hola mundo")
        long_text = "a" * 200
        self.assertLessEqual(len(truncate(long_text, 160)), 161)

    def test_book_slug(self):
        from core.seo import book_slug
        self.assertEqual(book_slug({"title": "El Quijote", "author": "Cervantes"}),
                         "el-quijote-cervantes")
        self.assertEqual(book_slug({}), "libro")

    def test_strip_html(self):
        from core.seo import strip_html
        self.assertEqual(strip_html("<p>Hola <b>mundo</b></p>"), "Hola mundo")

    def test_absolute_url_resolves_remote_prefix(self):
        """Las portadas con prefijo `remote:` se traducen a una URL HTTP pública
        para que los crawlers (OG/Twitter/Google) puedan cargarlas."""
        from core.seo import absolute_url
        # Sin request: cae en SITE_URL (puede estar vacío en test); lo importante
        # es que el prefijo `remote:` se transforme a /api/remote/file/cover/*.
        from django.test import RequestFactory
        req = RequestFactory().get("/")
        url = absolute_url(req, "remote:mi-libro.jpg")
        self.assertIn("/api/remote/file/cover/mi-libro.jpg", url)
        self.assertFalse(url.startswith("remote:"))
