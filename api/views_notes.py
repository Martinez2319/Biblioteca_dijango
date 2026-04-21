from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from bson import ObjectId
from datetime import datetime, timezone
import json

from .db import notes_collection
from .decorators import auth_required

@auth_required
@require_http_methods(["GET"])
def get_notes(request, book_id):
    """Obtener todas las notas de un libro para el usuario"""
    try:
        user_id = request.user_data.get('id')
        notes = list(notes_collection().find({
            'userId': user_id,
            'bookId': book_id
        }).sort('createdAt', -1))
        
        for note in notes:
            note['id'] = str(note['_id'])
            del note['_id']
        
        return JsonResponse(notes, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@auth_required
@require_http_methods(["POST"])
def create_note(request, book_id):
    """Crear una nota o resaltado"""
    try:
        user_id = request.user_data.get('id')
        data = json.loads(request.body)
        
        note = {
            'userId': user_id,
            'bookId': book_id,
            'text': data.get('text', ''),  # Texto resaltado
            'note': data.get('note', ''),  # Nota del usuario
            'page': data.get('page', 1),
            'color': data.get('color', 'yellow'),  # yellow, green, blue, pink
            'position': data.get('position', {}),  # {start, end} para ubicar el texto
            'createdAt': datetime.now(timezone.utc)
        }
        
        result = notes_collection().insert_one(note)
        note['id'] = str(result.inserted_id)
        del note['_id']
        note['createdAt'] = note['createdAt'].isoformat()
        
        return JsonResponse(note)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@auth_required
@require_http_methods(["PUT"])
def update_note(request, book_id, note_id):
    """Actualizar una nota"""
    try:
        user_id = request.user_data.get('id')
        data = json.loads(request.body)
        
        result = notes_collection().update_one(
            {'_id': ObjectId(note_id), 'userId': user_id, 'bookId': book_id},
            {'$set': {
                'note': data.get('note', ''),
                'color': data.get('color', 'yellow'),
                'updatedAt': datetime.now(timezone.utc)
            }}
        )
        
        if result.modified_count == 0:
            return JsonResponse({'error': 'Nota no encontrada'}, status=404)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@auth_required
@require_http_methods(["DELETE"])
def delete_note(request, book_id, note_id):
    """Eliminar una nota"""
    try:
        user_id = request.user_data.get('id')
        
        result = notes_collection().delete_one({
            '_id': ObjectId(note_id),
            'userId': user_id,
            'bookId': book_id
        })
        
        if result.deleted_count == 0:
            return JsonResponse({'error': 'Nota no encontrada'}, status=404)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@auth_required
@require_http_methods(["GET"])
def get_all_user_notes(request):
    """Obtener todas las notas del usuario (para Mi Biblioteca)"""
    try:
        user_id = request.user_data.get('id')
        notes = list(notes_collection().find({'userId': user_id}).sort('createdAt', -1))
        
        for note in notes:
            note['id'] = str(note['_id'])
            del note['_id']
        
        return JsonResponse(notes, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

