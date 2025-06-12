# Archivo: main_bot.py (Versión Final y Robusta)

import os
import logging
import asyncio
import re
import threading
import traceback
import html
from dotenv import load_dotenv

from watcher import start_watcher_thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest
from telegram.constants import ParseMode

from ai_dispatcher_v2 import (
    process_request_v2,
    generate_proactive_strategy, 
    re_evaluate_strategy
)
from memory import add_to_history, get_history

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_KEY")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

generated_strategies = {}

def escape_html_tags(text: str) -> str:
    """Función de ayuda para escapar HTML de forma segura, permitiendo etiquetas específicas."""
    if not isinstance(text, str):
        return ""
    # Escapa todos los caracteres especiales de HTML (<, >, &)
    escaped_text = html.escape(text, quote=False)
    # Vuelve a habilitar las etiquetas que sí queremos permitir
    tags_to_allow = ["<b>", "</b>", "<i>", "</i>", "<code>", "</code>", "<pre>", "</pre>"]
    for tag in tags_to_allow:
        escaped_text = escaped_text.replace(html.escape(tag), tag)
    # Limpia cualquier etiqueta HTML no soportada que pudiera haberse colado
    return re.sub(r'</?(ul|li|h[1-6])>', '', escaped_text)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = "🚀 <b>Agente de Trading Proactivo v5.1</b>\n\nSoy tu asistente de IA para trading. Pídeme un análisis o una estrategia. Ahora con botones de acción rápida y envío de gráficos mejorado."
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
    await context.bot.send_message(chat_id=chat_id, text=adjusted_report, parse_mode=ParseMode.HTML)

async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    message = f"El ID de este chat es: <code>{chat_id}</code>"
    await update.message.reply_html(message)

async def handle_any_response(chat_id: int, context: ContextTypes.DEFAULT_TYPE, response_data: dict):
    """
    Función centralizada para enviar cualquier tipo de respuesta, manejando la lógica de mensajes separados.
    """
    text_response = response_data.get("text")
    chart_path = response_data.get("chart_path")
    asset = response_data.get("asset")
    timeframe = response_data.get("timeframe")

    try:
        # 1. Enviar el gráfico primero, si existe.
        if chart_path and os.path.exists(chart_path):
            await context.bot.send_photo(chat_id=chat_id, photo=open(chart_path, 'rb'))
            os.remove(chart_path)

        # 2. Enviar el texto después, si existe.
        if text_response:
            keyboard = []
            if asset:
                next_tf = "4h" if timeframe == "1h" else "1d" if timeframe == "4h" else "1h"
                keyboard.append(InlineKeyboardButton(f"📊 Analizar en {next_tf}", callback_data=f"reanalyze:{asset}:{next_tf}"))
                keyboard.append(InlineKeyboardButton("💡 Generar Estrategia", callback_data=f"strategy:{asset}:{timeframe}"))
                keyboard.append(InlineKeyboardButton("📰 Ver Sentimiento", callback_data=f"sentiment:{asset}"))
            reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
            
            clean_text = escape_html_tags(text_response)
            await context.bot.send_message(
                chat_id=chat_id, 
                text=clean_text, 
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
    except BadRequest as e:
        logger.error(f"Error de BadRequest al enviar mensaje: {e}. Mensaje: {text_response}")
        plain_text = re.sub(r'<[^>]+>', '', text_response)
        await context.bot.send_message(chat_id=chat_id, text=f"Error de formato. Mostrando en texto plano:\n\n{plain_text}")
    except Exception as e:
        logger.error(f"Error general al enviar mensaje: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Ocurrió un error inesperado al enviar la respuesta.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja los mensajes de texto del usuario."""
    chat_id = update.effective_chat.id
    user_message = update.message.text
    logger.info(f"Usuario '{update.effective_user.first_name}' ({chat_id}): {user_message}")
    
    await context.bot.send_chat_action(chat_id=chat_id, action='typing')
    
    history = get_history(chat_id)
    response_data = await asyncio.to_thread(process_request_v2, user_message, history, chat_id)
    
    add_to_history(chat_id, "user", user_message)
    if response_data.get("text"):
        add_to_history(chat_id, "assistant", response_data["text"])
    
    await handle_any_response(chat_id, context, response_data)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las pulsaciones de los botones inline."""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    data = query.data
    logger.info(f"Botón presionado: {data} por el usuario {chat_id}")

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    parts = data.split(':')
    action = parts[0]
    asset = parts[1]
    
    user_message = ""
    if action == 'reanalyze':
        timeframe = parts[2]
        user_message = f"Análisis de {asset} en {timeframe}"
    elif action == 'strategy':
        timeframe = parts[2]
        user_message = f"Estrategia para {asset} en {timeframe} con $1000"
    elif action == 'sentiment':
        user_message = f"Sentimiento de {asset}"
    
    if not user_message: return

    history = get_history(chat_id)
    response_data = await asyncio.to_thread(process_request_v2, user_message, history, chat_id)
    
    add_to_history(chat_id, "user", user_message)
    if response_data.get("text"):
        add_to_history(chat_id, "assistant", response_data["text"])

    await handle_any_response(chat_id, context, response_data)
        
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Excepción al manejar un update:", exc_info=context.error)

def _build_final_report(event: dict, report_data: dict) -> str:
    """Construye el informe final y lo escapa para HTML seguro."""
    print("  -> Construyendo informe final optimizado...")
    asset_str = event.get('asset', 'N/A').upper()
    analysis_summary = event.get('analysis_summary', {})
    net_flow = analysis_summary.get('net_flow', 0)
    inflows = analysis_summary.get('exchange_inflows', 0)
    outflows = analysis_summary.get('exchange_outflows', 0)
    total_volume_usd = analysis_summary.get('total_volume_usd', 0)
    
    analysis_paragraph = escape_html_tags(report_data.get("analysis_text", "Análisis no disponible."))
    
    risk_data = report_data.get("risk_management", {})
    pos_size_str = f"${risk_data.get('position_size_usd', 0):,.2f}"
    leverage_str = f"{risk_data.get('leverage', 0):.1f}x"
    risk_amount_str = f"${risk_data.get('risk_amount', 0):,.2f}"

    message_lines = [
        f"<b>🐋 Análisis On-Chain: {asset_str}</b>", "",
        f"<b>📊 Actividad de Flujos</b>",
        f"• Entradas: <code>${inflows:,.0f}</code> 💰",
        f"• Salidas: <code>${outflows:,.0f}</code> 💸",
        f"• Flujo Neto: <code>${net_flow:,.0f}</code> ⚖️",
        f"• Volumen Total: <code>${total_volume_usd:,.0f}</code> 📈", "",
        f"<b>🎯 Veredicto y Plan</b>",
        f"<i>{analysis_paragraph}</i>", "",
        f"<b>🛡️ Gestión de Riesgo</b>",
        f"• Tamaño Posición: <code>{pos_size_str}</code>",
        f"• Apalancamiento: <code>{leverage_str}</code>",
        f"• Riesgo/Trade: <code>{risk_amount_str}</code>", "",
        f"<i>Para reajustar: /ajustar <code>capital</code></i>"
    ]
    return "\n".join(message_lines)

async def handle_whale_event(event: dict, context: ContextTypes.DEFAULT_TYPE):
    TARGET_CHAT_ID = int(os.getenv("TELEGRAM_TARGET_CHAT_ID", "0"))
    if TARGET_CHAT_ID == 0:
        logger.warning("TELEGRAM_TARGET_CHAT_ID no está configurado en .env. Las alertas proactivas no se enviarán.")
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
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=alert_message, parse_mode=ParseMode.HTML)
        
        report_data = await asyncio.to_thread(generate_proactive_strategy, event, 1000)
        
        if "error" in report_data:
            error_msg = f"❌ No se pudo generar el informe estratégico para <b>{asset}</b>. Razón: {report_data['error']}"
            await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=error_msg, parse_mode=ParseMode.HTML)
            return

        final_report_message = _build_final_report(event, report_data)
        await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=final_report_message, parse_mode=ParseMode.HTML)
        
        print("✅ ¡Informe final enviado con éxito!")
        generated_strategies[TARGET_CHAT_ID] = event
    except Exception as e:
        print(f"Error CRÍTICO durante el manejo del evento de ballena: {e}")
        traceback.print_exc()

def main() -> None:
    logger.info("🚀 Iniciando Agente de Trading Proactivo v5.1...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    loop = asyncio.get_event_loop()
    def thread_safe_callback(event: dict):
        asyncio.run_coroutine_threadsafe(handle_whale_event(event, application), loop)
    
    start_watcher_thread(thread_safe_callback)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ajustar", adjust_strategy_command))
    application.add_handler(CommandHandler("id", get_id_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot iniciado. El observador de ballenas y el manejador de botones están activos.")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()