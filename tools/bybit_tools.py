# Archivo: tools/bybit_tools.py

import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()

# Leemos el modo de operación del .env
USE_TESTNET = os.getenv("BYBIT_TESTNET_MODE", "True").lower() == "true"

# Distinguimos las claves a usar
if USE_TESTNET:
    API_KEY = os.getenv("PRUEBA_API_KEY")
    API_SECRET = os.getenv("PRUEBA_API_SECRET")
else:
    API_KEY = os.getenv("BYBIT_API_KEY")
    API_SECRET = os.getenv("BYBIT_API_SECRET")

session = None  # Inicializamos la sesión como None
try:
    session = HTTP(
        testnet=USE_TESTNET,
        api_key=API_KEY,
        api_secret=API_SECRET,
    )
    mode_message = "Testnet" if USE_TESTNET else "Mainnet (Mercado Real)"
    print(f"Sesión de Bybit inicializada en modo: {mode_message}")
    
except Exception as e:
    print(f"Error CRÍTICO al inicializar la sesión de Bybit: {e}")

def get_price(symbol: str) -> dict:
    """
    Obtiene el último precio para un símbolo dado desde Bybit.
    Devuelve un diccionario con el estado y los datos.
    """
    if not session:
        return {"success": False, "message": "Error: La sesión de Bybit no está disponible."}

    try:
        ticker_info = session.get_tickers(category="spot", symbol=symbol)
        
        if ticker_info.get('retCode') == 0 and ticker_info['result']['list']:
            price = ticker_info['result']['list'][0]['lastPrice']
            return {
                "success": True,
                "symbol": symbol,
                "price": price
            }
        else:
            return {
                "success": False,
                "message": f"⚠️ No se pudo encontrar el símbolo '{symbol}'. ¿Está escrito correctamente?"
            }

    except Exception as e:
        print(f"Error inesperado al obtener el precio de {symbol}: {e}")
        return {
            "success": False,
            "message": f"❌ Ocurrió un error al consultar el precio de {symbol}."
        }

def search_symbol(query: str) -> dict:
    """
    Busca todos los símbolos en Bybit que coincidan con una consulta.
    """
    if not session:
        return {"success": False, "message": "Error: La sesión de Bybit no está disponible."}

    query = query.upper()
    
    print(f"Buscando símbolos en Bybit que contengan '{query}'...")
    try:
        response = session.get_tickers(category="spot")
        
        if response.get('retCode') == 0 and response['result']['list']:
            all_symbols = [item['symbol'] for item in response['result']['list']]
            matching_symbols = [s for s in all_symbols if query in s]
            
            if matching_symbols:
                print(f"Símbolos encontrados: {matching_symbols}")
                return {
                    "success": True,
                    "symbols": matching_symbols
                }
            else:
                return {
                    "success": False,
                    "message": f"🤷 No se encontraron símbolos en Bybit que contengan '{query}'."
                }
        else:
            return {"success": False, "message": "No se pudo obtener la lista de símbolos de Bybit."}

    except Exception as e:
        print(f"Error inesperado al buscar símbolos: {e}")
        return {"success": False, "message": "Ocurrió un error técnico al buscar símbolos."}

# --- NUEVAS FUNCIONES AÑADIDAS ---

def get_top_traded(limit: int = 10) -> dict:
    """
    Obtiene los pares más negociados en Spot de las últimas 24 horas por volumen.
    """
    if not session:
        return {"success": False, "message": "La sesión de Bybit no está disponible."}

    try:
        response = session.get_tickers(category="spot")
        
        if response.get('retCode') == 0 and response['result']['list']:
            # Filtrar solo pares USDT y que no sean stablecoins contra stablecoins
            tickers = [
                t for t in response['result']['list'] 
                if t['symbol'].endswith('USDT') and t['symbol'] not in ['USDCUSDT', 'EURUSDT', 'DAIUSDT']
            ]
            
            # Convertir volumen de negocio a float para ordenar
            for ticker in tickers:
                ticker['turnover24h'] = float(ticker.get('turnover24h', 0))

            # Ordenar por volumen de negocio (turnover)
            sorted_tickers = sorted(tickers, key=lambda x: x['turnover24h'], reverse=True)
            
            top_tickers = [
                {
                    "symbol": t['symbol'],
                    "price": t['lastPrice'],
                    "volume_24h_usd": t['turnover24h']
                } 
                for t in sorted_tickers[:limit]
            ]
            
            return {"success": True, "data": top_tickers}
        else:
            return {"success": False, "message": "No se pudo obtener la lista de tickers de Bybit."}

    except Exception as e:
        print(f"Error inesperado al obtener los más negociados: {e}")
        return {"success": False, "message": "Ocurrió un error técnico al obtener los más negociados."}

def get_top_gainers(limit: int = 10) -> dict:
    """
    Obtiene los mayores ganadores en Spot de las últimas 24 horas.
    """
    if not session:
        return {"success": False, "message": "La sesión de Bybit no está disponible."}

    try:
        response = session.get_tickers(category="spot")
        
        if response.get('retCode') == 0 and response['result']['list']:
            # Filtrar pares USDT con volumen significativo para evitar ruido
            tickers = [
                t for t in response['result']['list'] 
                if t['symbol'].endswith('USDT') and float(t.get('turnover24h', 0)) > 100000
            ]

            # Convertir el cambio de precio a float para poder ordenar
            for ticker in tickers:
                ticker['price24hPcnt'] = float(ticker.get('price24hPcnt', 0))

            # Ordenar por el porcentaje de cambio en 24h
            sorted_tickers = sorted(tickers, key=lambda x: x['price24hPcnt'], reverse=True)
            
            top_gainers = [
                {
                    "symbol": t['symbol'],
                    "price": t['lastPrice'],
                    "change_24h_percent": t['price24hPcnt'] * 100 # Convertir a porcentaje
                }
                for t in sorted_tickers[:limit]
            ]
            
            return {"success": True, "data": top_gainers}
        else:
            return {"success": False, "message": "No se pudo obtener la lista de tickers de Bybit."}
            
    except Exception as e:
        print(f"Error inesperado al obtener los top gainers: {e}")
        return {"success": False, "message": "Ocurrió un error técnico al obtener los top gainers."}