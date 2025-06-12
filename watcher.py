# Archivo: watcher.py

import time
import threading
from typing import Callable
from tools.onchain_tools import analyze_whale_activity # Reutilizamos nuestra herramienta
from tools.ecosystem_tools import EcosystemMapper

# Umbrales para considerar un movimiento "significativo"
MIN_VOLUME_USD_TO_TRIGGER = 2_000_000  # $2 Millones
MIN_NET_FLOW_TO_TRIGGER = 1_000_000   # $1 Millón de flujo neto

# Almacenamiento simple en memoria para los hashes de transacciones ya procesadas
# En un sistema de producción, esto debería ser una base de datos como Redis para persistencia.
processed_whale_events = set()

def whale_watcher(callback: Callable[[dict], None], interval_seconds: int = 300):
    """
    Monitorea la actividad de ballenas para BTC y ETH en un bucle infinito.
    Cuando detecta un evento significativo y nuevo, invoca la función de callback.

    :param callback: La función a llamar cuando se detecta un evento.
    :param interval_seconds: Cada cuántos segundos revisar. 300s = 5 minutos.
    """
    print("🚀 Iniciando Observador de Ballenas (Whale Watcher)... (Revisará cada 5 minutos)")
    ecosystem_mapper = EcosystemMapper()
    
    while True:
        print(f"\n--- [Watcher] Revisando actividad on-chain... ({time.strftime('%H:%M:%S')}) ---")
        for asset in ["ethereum", "bitcoin"]:
            try:
                result = analyze_whale_activity(asset)
                if not result.get("success"):
                    print(f"  -> No se pudieron obtener datos para {asset.upper()}. Saltando...")
                    continue

                analysis = result.get("data", {}).get("whale_activity", {}).get("analysis", {})
                total_volume = analysis.get("total_volume_usd", 0)
                net_flow = analysis.get("net_flow", 0)
                
                # Crear un identificador único para este "estado" del mercado
                event_id = f"{asset}-{result.get('data', {}).get('whale_activity', {}).get('total_transfers', 0)}-{total_volume}"

                # CONDICIONES PARA DISPARAR EL EVENTO
                is_significant_event = (
                    total_volume > MIN_VOLUME_USD_TO_TRIGGER or
                    abs(net_flow) > MIN_NET_FLOW_TO_TRIGGER
                )
                
                is_new_event = event_id not in processed_whale_events

                if is_significant_event and is_new_event:
                    print(f"🔥🔥🔥 [Watcher] ¡EVENTO SIGNIFICATIVO DETECTADO PARA {asset.upper()}! 🔥🔥🔥")
                    processed_whale_events.add(event_id)
                    
                    # Enriquecer el evento con datos del ecosistema
                    parent_token = "ETH" if asset == "ethereum" else "BTC"
                    ecosystem_info = ecosystem_mapper.find_token_ecosystem(parent_token)
                    
                    # Construir el payload del evento
                    event_payload = {
                        "event_type": "whale_movement",
                        "asset": asset,
                        "parent_token": parent_token,
                        "analysis_summary": analysis,
                        "ecosystem_impact": ecosystem_info.get("related", []),
                        "full_analysis_data": result["data"]
                    }
                    
                    # Disparar el callback con el evento
                    callback(event_payload)
                else:
                    print(f"  -> Sin eventos nuevos o significativos para {asset.upper()}.")
                    
            except Exception as e:
                print(f"Error en el ciclo del watcher para {asset}: {e}")
        
        # Esperar para el siguiente ciclo de revisión
        print(f"--- [Watcher] Ciclo completado. Durmiendo por {interval_seconds} segundos... ---")
        time.sleep(interval_seconds)

# --- ESTA ES LA FUNCIÓN QUE FALTABA ---
def start_watcher_thread(callback: Callable[[dict], None]):
    """
    Inicia la función whale_watcher en un hilo separado para que no bloquee
    el proceso principal del bot de Telegram.
    """
    watcher_thread = threading.Thread(
        target=whale_watcher,
        args=(callback,),
        daemon=True  # Esto asegura que el hilo se cierre cuando el programa principal termine
    )
    watcher_thread.start()
    print("✅ Hilo del Observador de Ballenas iniciado.")
    return watcher_thread