from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # Autenticación y recuperación
    path('login', views.login_page, name='login'),
    path('register', views.register_page, name='register'),
    path('forgot-password', views.forgot_password_page, name='forgot_password'),
    path('reset-password', views.reset_password_page, name='reset_password'),
    path('verify-email', views.verify_email_page, name='verify_email_page'),
    path('auth/google/callback', views.google_callback_page, name='google_callback'),

    # Navegación pública
    path('catalog', views.catalog, name='catalog'),

    # Ficha de libro: la URL original se mantiene para no romper enlaces
    # existentes; añadimos una variante SEO-friendly con slug.
    path('book/<str:book_id>', views.book_detail, name='book_detail'),
    path('book/<slug:slug>/<str:book_id>', views.book_detail, name='book_detail_slug'),

    path('reader/<str:book_id>', views.reader, name='reader'),

    # Área privada
    path('dashboard', views.dashboard, name='dashboard'),
    path('my-library', views.my_library, name='my_library'),
    path('subscription', views.subscription_page, name='subscription'),
]
