from django.urls import path
from . import views_auth, views_books, views_categories, views_users, views_remote, views_paypal, views_stats
from . import views_user_features, views_reviews, views_bookmarks, views_notes, views_subscriptions
from . import views_google_auth

urlpatterns = [
    # Auth
    path('auth/register', views_auth.register, name='register'),
    path('auth/validate-signup', views_auth.validate_signup, name='validate_signup'),
    path('auth/login', views_auth.login, name='login'),
    path('auth/logout', views_auth.logout, name='logout'),
    path('auth/me', views_auth.me, name='me'),
    path('auth/google', views_google_auth.google_auth, name='google_auth'),
    
    # Books
    path('books', views_books.list_books, name='list_books'),
    path('books/featured', views_books.featured_books, name='featured_books'),
    path('books/recent', views_books.recent_books, name='recent_books'),
    path('books/new/create', views_books.create_book, name='create_book'),
    path('books/<str:book_id>', views_books.get_book, name='get_book'),
    path('books/<str:book_id>/update', views_books.update_book, name='update_book'),
    path('books/<str:book_id>/delete', views_books.delete_book, name='delete_book'),
    path('books/<str:book_id>/read', views_books.register_read, name='register_read'),
    
    # Categories
    path('categories', views_categories.list_categories, name='list_categories'),
    path('categories/create', views_categories.create_category, name='create_category'),
    path('categories/<str:cat_id>/update', views_categories.update_category, name='update_category'),
    path('categories/<str:cat_id>/delete', views_categories.delete_category, name='delete_category'),
    
    # Users
    path('users', views_users.list_users, name='list_users'),
    path('users/<str:user_id>/update', views_users.update_user, name='update_user'),
    path('users/<str:user_id>/delete', views_users.delete_user, name='delete_user'),
    
    # Remote PC
    path('remote/register', views_remote.register_pc, name='register_pc'),
    path('remote/heartbeat', views_remote.heartbeat, name='heartbeat'),
    path('remote/disconnect', views_remote.disconnect, name='disconnect'),
    path('remote/status', views_remote.status, name='remote_status'),
    path('remote/files', views_remote.list_files, name='remote_files'),
    path('remote/file/<str:file_type>/<str:filename>', views_remote.proxy_file, name='proxy_file'),
    
    # PayPal
    path('paypal/config', views_paypal.config, name='paypal_config'),
    path('paypal/create-order', views_paypal.create_order, name='create_order'),
    path('paypal/capture-order/<str:order_id>', views_paypal.capture_order, name='capture_order'),
    path('paypal', views_paypal.list_donations, name='list_donations'),
    
    # Stats & Seed
    path('stats', views_stats.stats, name='stats'),
    path('seed', views_stats.seed, name='seed'),
    
    # === FASE 2: Favorites, Progress, History ===
    path('favorites', views_user_features.get_favorites, name='get_favorites'),
    path('favorites/<str:book_id>', views_user_features.check_favorite, name='check_favorite'),
    path('favorites/<str:book_id>/toggle', views_user_features.toggle_favorite, name='toggle_favorite'),
    
    path('progress', views_user_features.get_all_progress, name='get_all_progress'),
    path('progress/<str:book_id>', views_user_features.get_progress, name='get_progress'),
    path('progress/<str:book_id>/save', views_user_features.save_progress, name='save_progress'),
    
    path('history', views_user_features.get_history, name='get_history'),
    path('history/clear', views_user_features.clear_history, name='clear_history'),
    
    # === FASE 3: Reviews & Notifications ===
    path('reviews/<str:book_id>', views_reviews.get_reviews, name='get_reviews'),
    path('reviews/<str:book_id>/create', views_reviews.create_review, name='create_review'),
    path('reviews/<str:book_id>/delete', views_reviews.delete_review, name='delete_review'),
    
    path('notifications', views_reviews.get_notifications, name='get_notifications'),
    path('notifications/<str:notif_id>/read', views_reviews.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all', views_reviews.mark_all_read, name='mark_all_read'),
    
    # === FASE 4: Bookmarks ===
    path('bookmarks/<str:book_id>', views_bookmarks.get_bookmarks, name='get_bookmarks'),
    path('bookmarks/<str:book_id>/create', views_bookmarks.create_bookmark, name='create_bookmark_direct'),
    path('bookmarks/<str:book_id>/<str:bookmark_id>', views_bookmarks.delete_bookmark, name='delete_bookmark'),

    # Auth - agregar estas rutas
    path('auth/verify-email', views_auth.verify_email, name='verify_email'),
    path('auth/resend-verification', views_auth.resend_verification, name='resend_verification'),
    path('auth/resend-verification-public', views_auth.resend_verification_public, name='resend_verification_public'),
    path('debug/session', views_auth.debug_session, name='debug_session'),

    # Books - agregar ruta de compra
    path('books/<str:book_id>/purchase', views_books.purchase_book, name='purchase_book'),
    
    # === FASE 5: Notes & Highlights ===
    path('notes/<str:book_id>', views_notes.get_notes, name='get_notes'),
    path('notes/<str:book_id>/create', views_notes.create_note, name='create_note'),
    path('notes/<str:book_id>/<str:note_id>', views_notes.update_note, name='update_note'),
    path('notes/<str:book_id>/<str:note_id>/delete', views_notes.delete_note, name='delete_note'),
    path('notes', views_notes.get_all_user_notes, name='get_all_user_notes'),
    
    # === FASE 6: Subscriptions ===
    path('subscriptions/plans', views_subscriptions.get_plans, name='get_plans'),
    path('subscriptions/current', views_subscriptions.get_subscription, name='get_subscription'),
    path('subscriptions/create', views_subscriptions.create_subscription, name='create_subscription'),
    path('subscriptions/cancel', views_subscriptions.cancel_subscription, name='cancel_subscription'),
]
