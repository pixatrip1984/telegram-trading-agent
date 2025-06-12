# Archivo: tools/analysis_tools.py

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional, Tuple

from .bybit_tools import session as bybit_session
from .binance_tools import get_historical_data_binance

# ... (todas las funciones desde get_historical_data_extended hasta perform_multi_timeframe_analysis no necesitan cambios) ...
def get_historical_data_extended(symbol: str, interval: str = 'D', limit: int = 1000) -> Optional[pd.DataFrame]:
    """
    Obtiene datos históricos extendidos y se asegura de que el índice sea DatetimeIndex.
    """
    symbol = symbol.upper()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'

    print(f"Iniciando búsqueda de datos históricos para {symbol}...")

    # Proveedor 1: Bybit
    print("-> Intentando obtener datos de Bybit...")
    df = get_historical_data_bybit(symbol, interval, limit)
    
    if df is not None and not df.empty:
        print("  -> Datos obtenidos exitosamente de Bybit.")
        df['source'] = 'Bybit'
        return df

    # Proveedor 2: Binance (fallback)
    print("  -> Fallo en Bybit. Intentando obtener datos de Binance...")
    interval_map_to_binance = {
        'D': '1d', 'W': '1w', 'M': '1M',
        '1': '1m', '3': '3m', '5': '5m', '15': '15m', '30m': '30m',
        '60': '1h', '120': '2h', '240': '4h', '360': '6h', '720': '12h'
    }
    bybit_api_interval = get_bybit_api_interval(interval)
    binance_interval = interval_map_to_binance.get(bybit_api_interval, bybit_api_interval)

    df_binance = get_historical_data_binance(symbol, binance_interval, limit)

    if df_binance is not None and not df_binance.empty:
        print("  -> Datos obtenidos exitosamente de Binance.")
        df_binance['source'] = 'Binance'
        if not isinstance(df_binance.index, pd.DatetimeIndex):
             df_binance['timestamp'] = pd.to_datetime(df_binance['timestamp'])
             df_binance = df_binance.set_index('timestamp')
        return df_binance

    print(f"❌ No se pudieron obtener datos para {symbol} en ninguna fuente.")
    return None

def get_bybit_api_interval(interval: str) -> str:
    interval_map = {
        '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
        '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
        '1d': 'D', '1w': 'W', '1M': 'M'
    }
    return interval_map.get(interval, interval)

def get_historical_data_bybit(symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
    api_interval = get_bybit_api_interval(interval)
    
    try:
        all_data = []
        max_limit_per_call = 1000
        # Bybit a veces devuelve los timestamps como strings, forzamos a numérico
        end_time = None
        remaining = limit

        while remaining > 0:
            current_limit = min(remaining, max_limit_per_call)
            params = {
                "category": "spot", "symbol": symbol, "interval": api_interval, "limit": current_limit
            }
            if end_time:
                params["end"] = end_time
            
            response = bybit_session.get_kline(**params)
            
            if response.get('retCode') == 0 and response['result']['list']:
                data = pd.DataFrame(
                    response['result']['list'], 
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                )
                
                # Evitar que la siguiente llamada pida el mismo timestamp
                end_time = int(data['timestamp'].min()) - 1
                
                all_data.append(data)
                remaining -= len(data)

                if len(data) < max_limit_per_call: # No hay más datos históricos
                    break
            else:
                if response.get('retCode') != 0 and response.get('retCode') != 10001: 
                    print(f"  Error de API Bybit: {response.get('retMsg')}")
                break
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'timestamp']
            combined_df[numeric_cols] = combined_df[numeric_cols].apply(pd.to_numeric)
            combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], unit='ms')
            
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='first')
            combined_df = combined_df.set_index('timestamp')
            return combined_df
        
        return None
        
    except Exception as e:
        print(f"Error obteniendo datos de Bybit: {e}")
        return None
def calculate_market_structure(df: pd.DataFrame) -> Dict:
    """Analiza la estructura del mercado (HH, HL, LL, LH)."""
    highs = df['high'].values
    lows = df['low'].values
    
    pivot_highs = []
    pivot_lows = []
    
    for i in range(2, len(df) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
           highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            pivot_highs.append((i, highs[i]))
        
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
           lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            pivot_lows.append((i, lows[i]))
    
    structure = "Indefinida"
    if len(pivot_highs) >= 2 and len(pivot_lows) >= 2:
        last_high = pivot_highs[-1][1]
        prev_high = pivot_highs[-2][1]
        last_low = pivot_lows[-1][1]
        prev_low = pivot_lows[-2][1]
        
        if last_high > prev_high and last_low > prev_low:
            structure = "Tendencia Alcista (HH-HL)"
        elif last_high < prev_high and last_low < prev_low:
            structure = "Tendencia Bajista (LH-LL)"
        else:
            structure = "Consolidación"
    
    return {
        "structure": structure,
        "pivot_highs": pivot_highs[-5:] if pivot_highs else [],
        "pivot_lows": pivot_lows[-5:] if pivot_lows else []
    }

def detect_chart_patterns(df: pd.DataFrame) -> List[Dict]:
    """Detecta patrones chartistas comunes."""
    patterns = []
    
    pattern_functions = {
        'Doji': talib.CDLDOJI,
        'Hammer': talib.CDLHAMMER,
        'Shooting Star': talib.CDLSHOOTINGSTAR,
        'Engulfing': talib.CDLENGULFING,
        'Morning Star': talib.CDLMORNINGSTAR,
        'Evening Star': talib.CDLEVENINGSTAR,
    }
    
    for pattern_name, pattern_func in pattern_functions.items():
        try:
            result = pattern_func(df['open'], df['high'], df['low'], df['close'])
            last_signal_index = result[result != 0].index.max()
            if pd.notna(last_signal_index) and (len(df) - df.index.get_loc(last_signal_index)) <= 5:
                last_signal = result.loc[last_signal_index]
                patterns.append({
                    "pattern": pattern_name,
                    "signal": "Bullish" if last_signal > 0 else "Bearish",
                    "location": f"hace {len(df) - 1 - df.index.get_loc(last_signal_index)} velas"
                })
        except:
            pass
    
    return patterns

def calculate_support_resistance_zones(df: pd.DataFrame, sensitivity: float = 0.02) -> Dict:
    """Calcula zonas de soporte y resistencia usando múltiples métodos."""
    closes = df['close'].values
    highs = df['high'].values
    lows = df['low'].values
    volumes = df['volume'].values
    
    current_price = closes[-1]
    
    pivot_levels = []
    for i in range(10, len(df) - 10):
        if highs[i] == max(highs[i-10:i+10]):
            pivot_levels.append(highs[i])
        if lows[i] == min(lows[i-10:i+10]):
            pivot_levels.append(lows[i])
    
    volume_profile = {}
    price_step = max(current_price * 0.001, 0.0001)
    
    for i, (price, vol) in enumerate(zip(closes, volumes)):
        price_bucket = round(price / price_step) * price_step
        if price_bucket not in volume_profile:
            volume_profile[price_bucket] = 0
        volume_profile[price_bucket] += vol
    
    volume_levels = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)[:10]
    high_volume_prices = [price for price, _ in volume_levels]
    
    all_levels = pivot_levels + high_volume_prices
    
    zones = []
    for level in sorted(list(set(all_levels))):
        if not zones or abs(zones[-1]['center'] - level) / level > sensitivity:
            zones.append({'center': level, 'levels': [level], 'strength': 1})
        else:
            zones[-1]['levels'].append(level)
            zones[-1]['center'] = np.mean(zones[-1]['levels'])
            zones[-1]['strength'] += 1
            
    support_zones = [z for z in zones if z['center'] < current_price]
    resistance_zones = [z for z in zones if z['center'] >= current_price]
    
    support_zones.sort(key=lambda x: x['center'], reverse=True)
    resistance_zones.sort(key=lambda x: x['center'])
    
    return {
        "support_zones": support_zones[:3],
        "resistance_zones": resistance_zones[:3],
        "current_price": current_price
    }

def perform_multi_timeframe_analysis(symbol: str, timeframes: Optional[List[str]] = None) -> Dict:
    """Realiza análisis en múltiples temporalidades."""
    if timeframes is None:
        timeframes = ['15m', '1h', '4h', '1d']

    mtf_analysis = {}
    
    for tf in timeframes:
        print(f"Analizando {symbol} en {tf}...")
        
        df = get_historical_data_extended(symbol, interval=tf, limit=500)
        if df is None or len(df) < 50:
            continue
        
        rsi = talib.RSI(df['close'], timeperiod=14)
        macd, signal, hist = talib.MACD(df['close'])
        
        sma_50 = talib.SMA(df['close'], timeperiod=50)
        sma_200 = talib.SMA(df['close'], timeperiod=200) if len(df) > 200 else None
        
        atr = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        
        current_close = df['close'].iloc[-1]
        trend = "Neutral"
        
        if sma_200 is not None and not pd.isna(sma_200.iloc[-1]) and not pd.isna(sma_50.iloc[-1]):
            if current_close > sma_50.iloc[-1] > sma_200.iloc[-1]:
                trend = "Fuerte Alcista"
            elif current_close < sma_50.iloc[-1] < sma_200.iloc[-1]:
                trend = "Fuerte Bajista"
            elif current_close > sma_200.iloc[-1]:
                trend = "Alcista"
            elif current_close < sma_200.iloc[-1]:
                trend = "Bajista"
        
        momentum = "Neutral"
        if not rsi.empty and not macd.empty:
            if rsi.iloc[-1] > 70: momentum = "Sobrecompra"
            elif rsi.iloc[-1] < 30: momentum = "Sobreventa"
            elif macd.iloc[-1] > signal.iloc[-1] and hist.iloc[-1] > 0: momentum = "Bullish"
            elif macd.iloc[-1] < signal.iloc[-1] and hist.iloc[-1] < 0: momentum = "Bearish"
        
        mtf_analysis[tf] = {
            "trend": trend,
            "momentum": momentum,
            "rsi": round(rsi.iloc[-1], 2) if not rsi.empty else None,
            "volatility_atr": round(atr.iloc[-1], 4) if not atr.empty else None
        }
    
    trends = [analysis["trend"] for analysis in mtf_analysis.values()]
    if not trends:
        return {"timeframes": mtf_analysis, "overall_bias": "Indeterminado", "alignment": False}

    bullish_count = sum(1 for t in trends if "Alcista" in t)
    bearish_count = sum(1 for t in trends if "Bajista" in t)
    
    if bullish_count > bearish_count and bullish_count >= len(trends) / 2:
        overall_bias = "BULLISH"
    elif bearish_count > bearish_count and bearish_count >= len(trends) / 2:
        overall_bias = "BEARISH"
    else:
        overall_bias = "NEUTRAL"
    
    return {
        "timeframes": mtf_analysis,
        "overall_bias": overall_bias,
        "alignment": bullish_count == len(trends) or bearish_count == len(trends)
    }

# --- FUNCIÓN CORREGIDA ---
def advanced_technical_analysis(symbol: str, interval: str = '1h') -> Dict:
    """Análisis técnico completo con todos los indicadores avanzados."""
    
    df = get_historical_data_extended(symbol, interval=interval, limit=1000)
    
    if df is None or len(df) < 200:
        return {"success": False, "message": f"Datos insuficientes para {symbol} en el intervalo {interval} desde todas las fuentes."}
    
    current_price = float(df['close'].iloc[-1])
    data_source = df['source'].iloc[-1]
    
    market_structure = calculate_market_structure(df)
    sr_zones = calculate_support_resistance_zones(df)
    patterns = detect_chart_patterns(df)
    
    indicators = {}
    indicators['SMA_50'] = talib.SMA(df['close'], 50).iloc[-1]
    indicators['SMA_200'] = talib.SMA(df['close'], 200).iloc[-1]
    indicators['RSI'] = talib.RSI(df['close'], 14).iloc[-1]
    macd, signal, hist = talib.MACD(df['close'])
    indicators['MACD'] = {"macd": macd.iloc[-1], "signal": signal.iloc[-1], "histogram": hist.iloc[-1]}
    bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], 20)
    indicators['Bollinger'] = {"upper": bb_upper.iloc[-1], "middle": bb_middle.iloc[-1], "lower": bb_lower.iloc[-1]}
    indicators['ATR'] = talib.ATR(df['high'], df['low'], df['close'], 14).iloc[-1]
    indicators['Volume_SMA'] = df['volume'].rolling(20).mean().iloc[-1]
    
    mtf = perform_multi_timeframe_analysis(symbol, ['15m', '1h', '4h'])
    signals = generate_trading_signals(df, indicators, patterns, sr_zones, mtf)
    
    return {
        "success": True,
        "data": {
            "symbol": symbol, "data_source": data_source, "current_price": current_price, 
            "market_structure": market_structure, "support_resistance": sr_zones, 
            "patterns": patterns, "indicators": indicators, "multi_timeframe": mtf, 
            "signals": signals, 
            # --- LÍNEA CORREGIDA: ACCEDER AL ÍNDICE ---
            "timestamp": df.index[-1].isoformat()
        }
    }
def generate_trading_signals(df: pd.DataFrame, indicators: Dict, 
                           patterns: List, sr_zones: Dict, mtf_analysis: Dict) -> Dict:
    """Genera señales de trading basadas en el análisis completo."""
    
    signals = {"bullish": [], "bearish": [], "neutral": []}
    current_price = float(df['close'].iloc[-1])

    # Señales de tendencia principal (Golden/Death Cross)
    if indicators.get('SMA_50') > indicators.get('SMA_200'):
        signals["bullish"].append("Tendencia alcista principal (Golden Cross)")
    elif indicators.get('SMA_50') < indicators.get('SMA_200'):
        signals["bearish"].append("Tendencia bajista principal (Death Cross)")

    # Señales de Momentum
    if indicators.get('RSI') < 30: signals["bullish"].append("RSI en Sobreventa (<30)")
    elif indicators.get('RSI') > 70: signals["bearish"].append("RSI en Sobrecompra (>70)")
    
    macd_hist = indicators.get('MACD', {}).get('histogram', 0)
    if macd_hist > 0: signals["bullish"].append("Histograma MACD positivo")
    else: signals["bearish"].append("Histograma MACD negativo")

    # Señales de Volatilidad
    if current_price < indicators.get('Bollinger', {}).get('lower', current_price + 1):
        signals["bullish"].append("Precio tocando banda inferior de Bollinger")
    elif current_price > indicators.get('Bollinger', {}).get('upper', current_price - 1):
        signals["bearish"].append("Precio tocando banda superior de Bollinger")

    # Señales de Patrones
    for p in patterns:
        if p['signal'] == 'Bullish': signals['bullish'].append(f"Patrón alcista: {p['pattern']}")
        else: signals['bearish'].append(f"Patrón bajista: {p['pattern']}")

    # Señales de Soportes y Resistencias
    if sr_zones['support_zones']:
        nearest_support = sr_zones['support_zones'][0]['center']
        if abs(current_price - nearest_support) / current_price < 0.01: # 1% de proximidad
            signals["bullish"].append(f"Cerca de zona de soporte clave (~${nearest_support:.2f})")
            
    if sr_zones['resistance_zones']:
        nearest_resistance = sr_zones['resistance_zones'][0]['center']
        if abs(current_price - nearest_resistance) / current_price < 0.01:
            signals["bearish"].append(f"Cerca de zona de resistencia clave (~${nearest_resistance:.2f})")

    # Señal de Alineación Multi-Timeframe
    if mtf_analysis.get('alignment'):
        if mtf_analysis.get('overall_bias') == 'BULLISH':
            signals['bullish'].append("Alineación alcista en múltiples temporalidades")
        elif mtf_analysis.get('overall_bias') == 'BEARISH':
            signals['bearish'].append("Alineación bajista en múltiples temporalidades")

    bull_score = len(signals["bullish"])
    bear_score = len(signals["bearish"])
    
    if bull_score > bear_score + 1: overall_signal = "COMPRA"
    elif bear_score > bull_score + 1: overall_signal = "VENTA"
    else: overall_signal = "NEUTRAL"
    
    if mtf_analysis.get('alignment') and abs(bull_score - bear_score) > 2:
        overall_signal = f"FUERTE {overall_signal}"

    return {
        "signals": signals, "overall": overall_signal,
        "confidence": abs(bull_score - bear_score) / max(bull_score + bear_score, 1) * 100,
        "score": {"bullish": bull_score, "bearish": bear_score}
    }