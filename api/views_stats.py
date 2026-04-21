import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime, timezone

from .db import books_collection, users_collection, categories_collection
from .decorators import admin_required
from .auth_utils import hash_password

@require_http_methods(["GET"])
@admin_required
def stats(request):
    try:
        total_books = books_collection().count_documents({})
        total_users = users_collection().count_documents({})
        total_categories = categories_collection().count_documents({})
        
        return JsonResponse({
            'totalBooks': total_books,
            'totalUsers': total_users,
            'totalCategories': total_categories
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def seed(request):
    try:
        if books_collection().count_documents({}) > 0:
            return JsonResponse({'message': 'Ya hay datos'})

        # Crear admin
        users_collection().insert_one({
            'name': 'Administrador',
            'email': 'admin@biblioteca.com',
            'passwordHash': hash_password('admin123'),
            'role': 'admin',
            'createdAt': datetime.now(timezone.utc)
        })

        # Crear categorías
        categories_collection().insert_many([
            {'name': 'Ficción', 'slug': 'ficcion', 'description': 'Novelas y cuentos', 'createdAt': datetime.now(timezone.utc)},
            {'name': 'Ciencia Ficción', 'slug': 'ciencia-ficcion', 'description': 'Futuros y tecnología', 'createdAt': datetime.now(timezone.utc)},
            {'name': 'Romance', 'slug': 'romance', 'description': 'Historias de amor', 'createdAt': datetime.now(timezone.utc)},
            {'name': 'Misterio', 'slug': 'misterio', 'description': 'Thrillers y detective', 'createdAt': datetime.now(timezone.utc)},
            {'name': 'Historia', 'slug': 'historia', 'description': 'Historia mundial', 'createdAt': datetime.now(timezone.utc)},
            {'name': 'Tecnología', 'slug': 'tecnologia', 'description': 'Ciencia y programación', 'createdAt': datetime.now(timezone.utc)},
        ])

        # Crear libros
        books_collection().insert_many([
            {
                'title': 'Cien Años de Soledad',
                'author': 'Gabriel García Márquez',
                'description': 'Obra maestra del realismo mágico.',
                'categories': ['Ficción'],
                'coverUrl': 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400',
                'content': 'Muchos años después, frente al pelotón de fusilamiento...',
                'views': 1250,
                'createdAt': datetime.now(timezone.utc)
            },
            {
                'title': '1984',
                'author': 'George Orwell',
                'description': 'Novela distópica sobre un futuro totalitario.',
                'categories': ['Ciencia Ficción', 'Ficción'],
                'coverUrl': 'https://images.unsplash.com/photo-1543002588-bfa74002ed7e?w=400',
                'content': 'Era un día luminoso y frío de abril...',
                'views': 980,
                'createdAt': datetime.now(timezone.utc)
            },
            {
                'title': 'El Principito',
                'author': 'Antoine de Saint-Exupéry',
                'description': 'Clásico sobre un pequeño príncipe.',
                'categories': ['Ficción'],
                'coverUrl': 'https://images.unsplash.com/photo-1589998059171-988d887df646?w=400',
                'content': 'Una vez, cuando tenía seis años...',
                'views': 1500,
                'createdAt': datetime.now(timezone.utc)
            },
            {
                'title': 'Don Quijote',
                'author': 'Miguel de Cervantes',
                'description': 'La obra maestra española.',
                'categories': ['Ficción', 'Historia'],
                'coverUrl': 'https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400',
                'content': 'En un lugar de la Mancha...',
                'views': 750,
                'createdAt': datetime.now(timezone.utc)
            }
        ])

        return JsonResponse({'message': 'Datos creados', 'books': 4, 'categories': 6})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
