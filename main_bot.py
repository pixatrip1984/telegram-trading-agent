# Archivo: main_bot_v2.py

import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

from ai_dispatcher_v2 import process_request_v2
from memory import add_to_history, get_history, clear_history, get_state, set_state, retrieve_data

# Cargar variables de entorno
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_KEY")

# Configuración del logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /start mejorado con menú de opciones."""
    chat_id = update.effective_chat.id
    clear_history(chat_id)
    
    # Crear teclado inline con opciones principales
    keyboard = [
        [
            InlineKeyboardButton("📊 Análisis Técnico", callback_data="menu_analysis"),
            InlineKeyboardButton("💰 Estrategia Completa", callback_data="menu_strategy")
        ],
        [
            InlineKeyboardButton("🌐 Análisis Ecosistema", callback_data="menu_ecosystem"),
            InlineKeyboardButton("📰 Sentimiento", callback_data="menu_sentiment"),
        ],
        [
            InlineKeyboardButton("📈 Top Ganadores", callback_data="menu_gainers"),
            InlineKeyboardButton("📉 Top Negociados", callback_data="menu_traded"),
        ],
        [
            InlineKeyboardButton("❓ Ayuda", callback_data="menu_help")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
🚀 <b>Agente de Trading Avanzado v3.0 - Restaurado</b>

Soy tu asistente de trading con IA, ahora más estable y potente.

• Análisis técnico y de ecosistema.
• Estrategias adaptadas y sentimiento de mercado.
• Detección de patrones y niveles clave.

<i>Selecciona una opción o escríbeme directamente.</i>
"""
    
    await update.message.reply_html(
        welcome_message,
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /help con ejemplos de uso."""
    help_text = """
📚 <b>Guía de Uso Avanzada</b>

<b>🎯 Estrategias Completas:</b>
• <code>Dame una estrategia para Bitcoin con 100 usd</code>
• <code>Predicción de ETH, tengo $500, riesgo alto</code>

<b>📊 Análisis Técnico:</b>
• <code>Análisis técnico de PEPE en 4h</code>
• <code>AT de Solana en 4 horas</code>

<b>🌐 Análisis de Ecosistema:</b>
• <code>Ecosistema de Solana</code>
• <code>Relaciones del token ARB</code>

<b>📰 Sentimiento de Mercado:</b>
• <code>Sentimiento de DOGE en twitter</code>
• <code>Informe de mercado de hoy</code>

<b>💡 Tips Pro:</b>
• Especifica capital y riesgo para estrategias personalizadas.
• Pide `Top Ganadores` y `Top Negociados` y luego `compara las listas`.
"""
    
    await update.message.reply_html(help_text)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /settings para configurar preferencias."""
    keyboard = [
        [
            InlineKeyboardButton("💵 Cambiar Capital", callback_data="set_capital"),
            InlineKeyboardButton("⚡ Nivel de Riesgo", callback_data="set_risk")
        ],
        [
            InlineKeyboardButton("⏰ Timeframe Preferido", callback_data="set_timeframe")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        "<b>⚙️ Configuración de Trading</b>\n\n"
        "Ajusta tus preferencias para recibir estrategias personalizadas:",
        reply_markup=reply_markup
    )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las interacciones con botones inline."""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    option = query.data.replace("menu_", "")
    
    prompts = {
        "analysis": "Por favor, dime qué activo quieres analizar. Ejemplo: <code>Análisis técnico de BTC</code>",
        "strategy": "Especifica el activo y tu capital. Ejemplo: <code>Estrategia para ETH con 100 usd</code>",
        "ecosystem": "¿De qué activo quieres el mapa de ecosistema? Ejemplo: <code>Ecosistema de SOL</code>",
        "sentiment": "¿De qué activo quieres ver el sentimiento? Ejemplo: <code>Sentimiento de DOGE</code>",
    }
    
    if query.data.startswith("menu_"):
        if option in prompts:
            await query.edit_message_text(prompts[option], parse_mode='HTML')
        elif option == "help":
            await help_command(query, context)
        elif option in ["gainers", "traded"]:
            message_text = "top ganadores" if option == "gainers" else "mas negociados"
            await query.edit_message_text(f"🔄 Obteniendo {message_text}...")
            response = process_request_v2(message_text, [], chat_id)
            await query.edit_message_text(response, parse_mode='HTML')
    
    elif query.data.startswith("set_"):
        # Lógica de configuración... (sin cambios)
        pass # Añadir lógica de settings si es necesario
    
    elif query.data.startswith("risk_") or query.data.startswith("tf_"):
        # Lógica de guardado de configuración... (sin cambios)
        pass # Añadir lógica de guardado si es necesario

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja todos los mensajes de texto."""
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    logger.info(f"Usuario '{update.effective_user.first_name}' ({chat_id}): {user_message}")
    
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    history = get_history(chat_id)
    
    # Agregar preferencias del usuario al contexto
    user_prefs = []
    if context.user_data.get('capital'): user_prefs.append(f"capital: {context.user_data['capital']}")
    if context.user_data.get('risk_level'): user_prefs.append(f"riesgo: {context.user_data['risk_level']}")
    if context.user_data.get('timeframe'): user_prefs.append(f"timeframe: {context.user_data['timeframe']}")
    
    if user_prefs:
        user_message += f" [Prefs: {', '.join(user_prefs)}]"

    response_text = process_request_v2(user_message, history, chat_id)
    
    add_to_history(chat_id, "user", user_message)
    add_to_history(chat_id, "assistant", response_text)
    
    await send_formatted_message(update.message, response_text)

# --- FUNCIÓN DE ENVÍO DE MENSAJES RESTAURADA Y SIMPLIFICADA ---
async def send_formatted_message(message, text: str) -> None:
    """Envía mensaje con formato HTML, dividiéndolo de forma inteligente si es muy largo."""
    MAX_LENGTH = 4096
    
    try:
        # Si el texto es demasiado largo, se divide por saltos de línea para no romper el formato
        if len(text) > MAX_LENGTH:
            parts = []
            current_part = ""
            lines = text.split('\n')
            for line in lines:
                if len(current_part) + len(line) + 1 > MAX_LENGTH:
                    parts.append(current_part)
                    current_part = line
                else:
                    current_part += '\n' + line
            if current_part:
                parts.append(current_part)

            for part in parts:
                if part.strip():
                    await message.reply_html(part)
        else:
            await message.reply_html(text)

    except BadRequest as e:
        logger.warning(f"Error al enviar mensaje con formato HTML: {e}. Reintentando como texto plano.")
        # Si falla el HTML, se limpia el formato y se envía como texto plano
        clean_text = re.sub(r'<[^>]*>', '', text)
        if len(clean_text) > MAX_LENGTH:
            for i in range(0, len(clean_text), MAX_LENGTH):
                await message.reply_text(clean_text[i:i+MAX_LENGTH])
        elif clean_text.strip():
            await message.reply_text(clean_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja errores de forma elegante."""
    logger.error(f"Update {update} causó error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Ocurrió un error procesando tu solicitud. "
                "Por favor, intenta de nuevo o reformula tu pregunta."
            )
    except:
        pass

def main() -> None:
    """Función principal que inicia el bot."""
    logger.info("🚀 Iniciando Agente de Trading Avanzado v3.0 - Restaurado...")
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot iniciado y escuchando actualizaciones.")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()