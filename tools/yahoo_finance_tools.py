# Archivo: tools/yahoo_finance_tools.py

import yfinance as yf
import pandas as pd
from typing import Optional, Dict, List

# Mapeo de nombres comunes a tickers de yfinance
TICKER_MAP = {
    "SP500": "^GSPC",
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW JONES": "^DJI",
    "ORO": "GC=F",
    "GOLD": "GC=F",
    "PETROLEO": "CL=F",
    "OIL": "CL=F",
    "VIX": "^VIX",
    "NIKKEI": "^N225",
    "HANG SENG": "^HSI",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "USD INDEX": "DX-Y.NYB",
    "DXY": "DX-Y.NYB",
}

def get_market_data_yf(ticker: str) -> Optional[pd.DataFrame]:
    """
    Obtiene datos históricos para un ticker de Yahoo Finance.
    El ticker debe ser válido para yfinance (ej. 'AAPL', '^GSPC').
    """
    try:
        # Normalizar ticker: buscar en el mapa, si no, usarlo directamente
        normalized_ticker = TICKER_MAP.get(ticker.upper(), ticker.upper())
        
        print(f"Buscando en Yahoo Finance: {ticker} (ticker: {normalized_ticker})...")
        
        stock = yf.Ticker(normalized_ticker)
        # 'max' obtiene todos los datos disponibles. Podemos limitarlo si es necesario.
        hist = stock.history(period="5y") 
        
        if hist.empty:
            print(f"  -> No se encontraron datos para {normalized_ticker} en Yahoo Finance.")
            return None
        
        # Renombrar columnas para que coincidan con nuestro formato estándar
        hist = hist.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Asegurar que el índice (fecha) sea una columna 'timestamp'
        hist['timestamp'] = hist.index
        
        print(f"  -> Datos de Yahoo Finance obtenidos exitosamente ({len(hist)} velas).")
        return hist[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    except Exception as e:
        print(f"Error al obtener datos de Yahoo Finance para {ticker}: {e}")
        return None

def get_multiple_indices_summary() -> Optional[Dict[str, Dict]]:
    """
    Obtiene un resumen rápido del estado actual de los principales índices mundiales.
    """
    indices = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "ORO": "GC=F",
        "PETROLEO": "CL=F",
        "VIX": "^VIX",
        "NIKKEI 225": "^N225"
    }
    
    summary = {}
    
    print("Obteniendo resumen de índices globales de Yahoo Finance...")
    
    for name, ticker_symbol in indices.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # 'info' es un dict con muchos datos, 'previousClose' y 'regularMarketOpen' son útiles
            info = ticker.info
            
            previous_close = info.get('previousClose', 0)
            current_price = info.get('regularMarketPrice', info.get('regularMarketOpen', 0))
            
            if previous_close > 0 and current_price > 0:
                change_pct = ((current_price - previous_close) / previous_close) * 100
                summary[name] = {
                    "price": round(current_price, 2),
                    "change_pct": round(change_pct, 2)
                }
            else:
                # A veces para futuros, los datos están en otros campos
                hist = ticker.history(period="2d")
                if not hist.empty:
                     previous_close = hist['close'].iloc[-2]
                     current_price = hist['close'].iloc[-1]
                     change_pct = ((current_price - previous_close) / previous_close) * 100
                     summary[name] = {
                         "price": round(current_price, 2),
                         "change_pct": round(change_pct, 2)
                     }

        except Exception as e:
            print(f"  -> No se pudo obtener resumen para {name}: {e}")
            continue
            
    return summary