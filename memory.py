# Archivo: memory.py

import re # <-- ¡LA LÍNEA QUE FALTABA!

# La memoria ahora guarda historial, estado y datos generados.
chat_sessions = {}
MAX_HISTORY_LENGTH = 12 

def _ensure_session(chat_id: int):
    """Asegura que una sesión exista para el chat_id dado."""
    if chat_id not in chat_sessions:
        chat_sessions[chat_id] = {
            'history': [], 
            'state': 'idle',
            'data_store': {}  # El almacén de contexto
        }

def get_history(chat_id: int) -> list:
    """Obtiene el historial de mensajes de una sesión."""
    _ensure_session(chat_id)
    return chat_sessions[chat_id]['history'].copy()

def add_to_history(chat_id: int, role: str, content: str):
    """Añade un mensaje al historial de una sesión."""
    _ensure_session(chat_id)
    # Limpiar el contenido de etiquetas HTML para el historial de la IA
    # Esto es importante para que la IA no se confunda con el formato
    clean_content = content.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '').replace('<code>', '').replace('</code>', '')
    clean_content = re.sub(r'<h[1-6]>.*?</h[1-6]>', '', clean_content, flags=re.DOTALL) # Quitar títulos
    
    chat_sessions[chat_id]['history'].append({"role": role, "content": clean_content})
    
    # Mantiene el historial con una longitud máxima
    if len(chat_sessions[chat_id]['history']) > MAX_HISTORY_LENGTH:
        chat_sessions[chat_id]['history'] = chat_sessions[chat_id]['history'][-MAX_HISTORY_LENGTH:]

def get_state(chat_id: int) -> str:
    """Obtiene el estado actual de la conversación."""
    _ensure_session(chat_id)
    return chat_sessions[chat_id]['state']

def set_state(chat_id: int, state: str):
    """Establece un nuevo estado para la conversación."""
    _ensure_session(chat_id)
    if state in ['idle', 'awaiting_followup']:
        chat_sessions[chat_id]['state'] = state
        print(f"--- Estado para chat {chat_id} cambiado a: {state} ---")
    else:
        print(f"Error: Intento de establecer un estado inválido '{state}'")

def store_data(chat_id: int, key: str, data: any):
    """Guarda datos en el almacén de la sesión."""
    _ensure_session(chat_id)
    chat_sessions[chat_id]['data_store'][key] = data
    print(f"--- Datos guardados para chat {chat_id} en la clave '{key}' ---")

def retrieve_data(chat_id: int, key: str) -> any:
    """Recupera datos del almacén de la sesión."""
    _ensure_session(chat_id)
    return chat_sessions[chat_id]['data_store'].get(key, None)

def clear_history(chat_id: int) -> bool:
    """Limpia la sesión completa (historial, estado y datos)."""
    if chat_id in chat_sessions:
        chat_sessions.pop(chat_id)
        print(f"Sesión completa para el chat {chat_id} ha sido limpiada.")
    return True