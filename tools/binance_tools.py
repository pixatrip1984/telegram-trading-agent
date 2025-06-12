# Archivo: tools/binance_tools.py

import os
import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = None
try:
    if API_KEY and API_SECRET:
        client = Client(API_KEY, API_SECRET)
        print("Cliente de Binance inicializado correctamente.")
    else:
        print("⚠️ ADVERTENCIA: Claves de API de Binance no encontradas.")
except Exception as e:
    print(f"Error CRÍTICO al inicializar el cliente de Binance: {e}")


def get_historical_data_binance(symbol: str, interval: str, limit: int = 1000) -> Optional[pd.DataFrame]:
    """
    Obtiene datos históricos de Binance y establece el timestamp como índice.
    """
    if not client:
        return None
        
    try:
        print(f"Buscando en Binance: {symbol} en intervalo {interval}...")
        
        klines = client.get_historical_klines(symbol, interval, limit=limit)
        
        if not klines:
            print(f"  -> No se encontraron datos para {symbol} en Binance.")
            return None

        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])

        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        # --- INICIO DE LA CORRECCIÓN ---
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        # LÍNEA CLAVE: Establecer el timestamp como el índice del DataFrame
        df = df.set_index('timestamp')
        # --- FIN DE LA CORRECCIÓN ---
        
        print(f"  -> Datos de Binance obtenidos exitosamente ({len(df)} velas).")
        return df

    except Exception as e:
        print(f"Error al obtener datos de Binance para {symbol}: {e}")
        return None