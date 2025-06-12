# Archivo: main_bot.py (Versión Final y Limpia)

import os
import logging
import asyncio
import re
import threading
import traceback
from dotenv import load_dotenv
from watcher import start_watcher_thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
# --- Añadido para escapar HTML ---
import html

from ai_dispatcher_v2 import (
    process_request_v2, 
    generate_proactive_strategy, 
    re_evaluate_strategy
)
from memory import (
    add_to_history, 
    get_history, 
    clear_history
)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_KEY")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

generated_strategies = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = "🚀 <b>Agente de Trading Proactivo v4.0</b>\n\nSoy tu asistente de IA para trading. Pídeme un análisis o una estrategia. Además, te enviaré <b>alertas proactivas</b> cuando detecte movimientos de ballenas importantes."
    await update.message.reply_html(welcome_message)

async def adjust_strategy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id not in generated_strategies:
        await update.message.reply_text("Primero debe generarse una alerta de ballenas para poder ajustar una estrategia.")
        return
        
    try:
        new_capital = float(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Por favor, proporciona un capital válido. Ejemplo: /ajustar 500")
        return
        
    await update.message.reply_text(f"🔄 Re-ajustando la última estrategia para un capital de ${new_capital}...")
    
    last_event = generated_strategies[chat_id]
    adjusted_report = await asyncio.to_thread(re_evaluate_strategy, last_event, new_capital)
    
    await context.bot.send_message(chat_id=chat_id, text=adjusted_report, parse_mode='HTML')

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    message = f"El ID de este chat es: <code>{chat_id}</code>"
    await update.message.reply_html(message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja todos los mensajes de texto del usuario, envía fotos y escapa HTML."""
    chat_id = update.effective_chat.id
    user_message = update.message.text
    logger.info(f"Usuario '{update.effective_user.first_name}' ({chat_id}): {user_message}")
    
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    history = get_history(chat_id)
    response_data = await asyncio.to_thread(process_request_v2, user_message, history, chat_id)
    
    text_response = response_data.get("text")
    if text_response is None:
        text_response = "Lo siento, ocurrió un error al generar la respuesta de texto."
        logger.error("response_data.get('text') devolvió None.")
    
    chart_path = response_data.get("chart_path")
    
    add_to_history(chat_id, "user", user_message)
    add_to_history(chat_id, "assistant", text_response)
    
    # --- INICIO DE LA CORRECCIÓN DE ESCAPE ---
    # Escapamos los caracteres '<', '>', y '&' para evitar que Telegram los interprete como HTML,
    # excepto para nuestras etiquetas permitidas (b, i, code, etc.).
    # Esta es una forma segura de hacerlo:
    # 1. Escapamos TODO.
    escaped_text = html.escape(text_response)
    # 2. Re-habilitamos nuestras etiquetas permitidas.
    tags_to_allow = ["<b>", "</b>", "<i>", "</i>", "<code>", "</code>", "<pre>", "</pre>", "<a>", "</a>"]
    for tag in tags_to_allow:
        escaped_tag = html.escape(tag)
        escaped_text = escaped_text.replace(escaped_tag, tag)
    
    # También limpiamos etiquetas no soportadas por si acaso
    clean_text = re.sub(r'</?(ul|li|h[1-6])>', '', escaped_text)
    # --- FIN DE LA CORRECCIÓN DE ESCAPE ---
    
    try:
        if chart_path and os.path.exists(chart_path):
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=open(chart_path, 'rb'),
                caption=clean_text,
                parse_mode='HTML'
            )
            os.remove(chart_path)
        else:
            await context.bot.send_message(chat_id=chat_id, text=clean_text, parse_mode='HTML')

    except BadRequest as e:
        logger.error(f"Error de BadRequest al enviar mensaje: {e}. Mensaje original: {clean_text}")
        plain_text = re.sub(r'<[^>]+>', '', clean_text)
        await context.bot.send_message(chat_id=chat_id, text=plain_text)
    except Exception as e:
        logger.error(f"Error general al enviar mensaje: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Ocurrió un error al formatear la respuesta.")

# ... (El resto del archivo no necesita cambios)
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Excepción al manejar un update:", exc_info=context.error)
def _build_final_report(event: dict, report_data: dict) -> str:
    print("  -> Construyendo informe final optimizado...")
    asset_str = event.get('asset', 'N/A').upper()
    analysis_summary = event.get('analysis_summary', {})
    net_flow = analysis_summary.get('net_flow', 0)
    inflows = analysis_summary.get('exchange_inflows', 0)
    outflows = analysis_summary.get('exchange_outflows', 0)
    total_volume_usd = analysis_summary.get('total_volume_usd', 0)
    analysis_paragraph = report_data.get("analysis_text", "Análisis no disponible.")
    risk_data = report_data.get("risk_management", {})
    pos_size_str = f"${risk_data.get('position_size_usd', 0):,.2f}"
    leverage_str = f"{risk_data.get('leverage', 0)}x"
    risk_amount_str = f"${risk_data.get('risk_amount', 0):,.2f}"
    message_lines = [
        f"<b>🐋 Análisis On-Chain: {asset_str}</b>", "",
        f"<b>📊 Actividad de Flujos</b>",
        f"• Entradas: <code>${inflows:,.0f}</code> 💰",
        f"• Salidas: <code>${outflows:,.0f}</code> 💸",
        f"• Flujo Neto: <code>${net_flow:,.0f}</code> ⚖️",
        f"• Volumen Total: <code>${total_volume_usd:,.0f}</code> 📈", "",
        f"<b>🎯 Veredicto y Plan</b>",
        f"<i>{analysis_paragraph}</i>",
        f"<b>🛡️ Gestión de Riesgo</b>",
        f"• Tamaño Posición: <code>{pos_size_str}</code>",
        f"• Apalancamiento: <code>{leverage_str}</code>",
        f"• Riesgo/Trade: <code>{risk_amount_str}</code>", "",
        f"<i>Para reajustar: /ajustar <code>capital</code></i>"
    ]
    return "\n".join(message_lines)
async def handle_whale_event(event: dict, context: ContextTypes.DEFAULT_TYPE):
    TARGET_CHAT_ID = int(os.getenv("TELEGRAM_TARGET_CHAT_ID", "7875913423"))
    if TARGET_CHAT_ID == 0:
        logger.warning("TELEGRAM_TARGET_CHAT_ID no está configurado. Las alertas proactivas no se enviarán.")
        return
    try:
        print(f"-> Iniciando manejo asíncrono del evento para {event.get('asset', 'N/A').upper()}...")
        asset = event.get('asset', 'Desconocido').upper()
        total_volume_usd = event.get('analysis_summary', {}).get('total_volume_usd', 0)
        net_flow = event.get('analysis_summary', {}).get('net_flow', 0)
        bias_text = "BAJISTA 📉" if net_flow < 0 else "ALCISTA 📈" if net_flow > 0 else "NEUTRAL ⚖️"
        total_volume_str = f"${total_volume_usd:,.0f}"
        alert_message = (
            f"<b>🚨 ALERTA DE BALLENAS:</b> MOVIMIENTO SIGNIFICATIVO EN {asset}\n\n"
            f"Volumen detectado: <b>{total_volume_str}</b>\n"
            f"Sesgo del flujo neto: <b>{bias_text}</b>\n\n"
            "<i>Generando análisis y estrategia completa...</i>"
        )
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=alert_message, parse_mode='HTML')
        report_data = await asyncio.to_thread(generate_proactive_strategy, event, 1000)
        if "error" in report_data:
            error_msg = f"❌ No se pudo generar el informe estratégico para <b>{asset}</b>. Razón: {report_data['error']}"
            await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=error_msg, parse_mode='HTML')
            return
        final_report_message = _build_final_report(event, report_data)
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_report_message, parse_mode='HTML')
        print("✅ ¡Informe final enviado con éxito!")
        generated_strategies[TARGET_CHAT_ID] = event
    except Exception as e:
        print(f"Error CRÍTICO durante el manejo del evento de ballena: {e}")
        traceback.print_exc()
        try:
            error_message = "❌ Ocurrió un error inesperado al procesar la alerta."
            await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=error_message)
        except Exception as send_error:
            print(f"No se pudo notificar al usuario del error: {send_error}")
def main() -> None:
    logger.info("🚀 Iniciando Agente de Trading Proactivo v4.0...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    loop = asyncio.get_event_loop()
    def thread_safe_callback(event: dict):
        print(f"-> [Callback Síncrono] Evento recibido en el hilo del watcher para {event['asset']}.")
        coro = handle_whale_event(event, application)
        asyncio.run_coroutine_threadsafe(coro, loop)
        print(f"-> [Callback Síncrono] Tarea para manejar el evento de {event['asset']} enviada al bucle principal.")
    start_watcher_thread(thread_safe_callback)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ajustar", adjust_strategy_command))
    application.add_handler(CommandHandler("id", get_id_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    logger.info("✅ Bot iniciado. El observador de ballenas está activo en segundo plano.")
    application.run_polling(drop_pending_updates=True)
if __name__ == '__main__':
    main()