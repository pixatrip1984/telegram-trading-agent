# Archivo: tools/analysis_tools_v2.py

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional, Tuple
from .bybit_tools import session

def get_historical_data_extended(symbol: str, interval: str = 'D', limit: int = 1000) -> pd.DataFrame | None:
    """
    Obtiene datos históricos extendidos haciendo múltiples llamadas.
    Puede obtener hasta 60,000 velas históricas.
    """
    # --- INICIO DE LA CORRECCIÓN ---
    # Diccionario para traducir intervalos de formato legible a formato de API Bybit v5
    interval_map = {
        '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
        '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
        '1d': 'D', '1w': 'W', '1M': 'M'
    }
    
    # Usar el valor del mapa, si no existe, usar el valor original (para 'D', 'W', etc.)
    api_interval = interval_map.get(interval, interval)
    # --- FIN DE LA CORRECCIÓN ---

    try:
        symbol = symbol.upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        all_data = []
        max_limit_per_call = 1000
        total_limit = min(limit, 60000)  # Máximo 60k
        
        print(f"Obteniendo {total_limit} velas para {symbol} en intervalo {api_interval}...")
        
        end_time = None
        remaining = total_limit
        
        while remaining > 0:
            current_limit = min(remaining, max_limit_per_call)
            
            params = {
                "category": "spot",
                "symbol": symbol,
                "interval": api_interval, # <-- Usar el intervalo corregido
                "limit": current_limit
            }
            
            if end_time:
                params["endTime"] = end_time
            
            response = session.get_kline(**params)
            
            if response.get('retCode') == 0 and response['result']['list']:
                data = pd.DataFrame(
                    response['result']['list'], 
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
                )
                
                # Convertir a numérico
                numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                data[numeric_cols] = data[numeric_cols].apply(pd.to_numeric)
                data['timestamp'] = pd.to_numeric(data['timestamp'])
                data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
                
                all_data.append(data)
                
                # Actualizar el end_time para la siguiente llamada
                end_time = int(data['timestamp'].min().timestamp() * 1000)
                remaining -= current_limit
                
                print(f"  Descargadas {total_limit - remaining}/{total_limit} velas...")
            else:
                if response.get('retCode') != 0:
                    print(f"  Error de API Bybit: {response.get('retMsg')}")
                break
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            combined_df = combined_df.drop_duplicates(subset=['timestamp'])
            
            print(f"Total de velas obtenidas: {len(combined_df)}")
            return combined_df
        
        return None
        
    except Exception as e:
        print(f"Error obteniendo datos históricos extendidos: {e}")
        return None

def calculate_market_structure(df: pd.DataFrame) -> Dict:
    """Analiza la estructura del mercado (HH, HL, LL, LH)."""
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    
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
        'Three White Soldiers': talib.CDL3WHITESOLDIERS,
        'Three Black Crows': talib.CDL3BLACKCROWS
    }
    
    for pattern_name, pattern_func in pattern_functions.items():
        try:
            result = pattern_func(df['open'], df['high'], df['low'], df['close'])
            last_signal = result.iloc[-1]
            
            if last_signal != 0:
                patterns.append({
                    "pattern": pattern_name,
                    "signal": "Bullish" if last_signal > 0 else "Bearish",
                    "strength": abs(last_signal),
                    "location": "Última vela"
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
    price_step = current_price * 0.001
    
    for i, (price, vol) in enumerate(zip(closes, volumes)):
        price_bucket = round(price / price_step) * price_step
        if price_bucket not in volume_profile:
            volume_profile[price_bucket] = 0
        volume_profile[price_bucket] += vol
    
    volume_levels = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)[:10]
    high_volume_prices = [price for price, _ in volume_levels]
    
    psychological_levels = []
    round_number = round(current_price, -int(np.log10(current_price)) + 1)
    for i in range(-5, 6):
        level = round_number + (round_number * 0.1 * i)
        if level > 0:
            psychological_levels.append(level)
    
    all_levels = pivot_levels + high_volume_prices + psychological_levels
    
    zones = []
    for level in sorted(set(all_levels)):
        merged = False
        for zone in zones:
            if abs(zone['center'] - level) / zone['center'] < sensitivity:
                zone['levels'].append(level)
                zone['center'] = np.mean(zone['levels'])
                zone['strength'] += 1
                merged = True
                break
        
        if not merged:
            zones.append({
                'center': level,
                'levels': [level],
                'strength': 1
            })
    
    support_zones = [z for z in zones if z['center'] < current_price]
    resistance_zones = [z for z in zones if z['center'] > current_price]
    
    support_zones.sort(key=lambda x: x['center'], reverse=True)
    resistance_zones.sort(key=lambda x: x['center'])
    
    return {
        "support_zones": support_zones[:3],
        "resistance_zones": resistance_zones[:3],
        "current_price": current_price
    }

def perform_multi_timeframe_analysis(symbol: str, timeframes: List[str] = None) -> Dict:
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
        
        sma_20 = talib.SMA(df['close'], timeperiod=20)
        sma_50 = talib.SMA(df['close'], timeperiod=50)
        sma_200 = talib.SMA(df['close'], timeperiod=200) if len(df) > 200 else None
        
        atr = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        atr_pct = (atr.iloc[-1] / df['close'].iloc[-1]) * 100
        
        current_close = df['close'].iloc[-1]
        trend = "Neutral"
        
        if sma_200 is not None and not pd.isna(sma_200.iloc[-1]):
            if current_close > sma_50.iloc[-1] > sma_200.iloc[-1]:
                trend = "Fuerte Alcista"
            elif current_close < sma_50.iloc[-1] < sma_200.iloc[-1]:
                trend = "Fuerte Bajista"
            elif current_close > sma_200.iloc[-1]:
                trend = "Alcista"
            elif current_close < sma_200.iloc[-1]:
                trend = "Bajista"
        
        momentum = "Neutral"
        if rsi.iloc[-1] > 70:
            momentum = "Sobrecompra"
        elif rsi.iloc[-1] < 30:
            momentum = "Sobreventa"
        elif macd.iloc[-1] > signal.iloc[-1] and hist.iloc[-1] > 0:
            momentum = "Bullish"
        elif macd.iloc[-1] < signal.iloc[-1] and hist.iloc[-1] < 0:
            momentum = "Bearish"
        
        mtf_analysis[tf] = {
            "trend": trend,
            "momentum": momentum,
            "rsi": round(rsi.iloc[-1], 2),
            "volatility": round(atr_pct, 2),
            "price": current_close,
            "distance_from_sma50": round((current_close - sma_50.iloc[-1]) / sma_50.iloc[-1] * 100, 2)
        }
    
    trends = [analysis["trend"] for analysis in mtf_analysis.values()]
    bullish_count = sum(1 for t in trends if "Alcista" in t)
    bearish_count = sum(1 for t in trends if "Bajista" in t)
    
    if bullish_count > bearish_count:
        overall_bias = "BULLISH"
    elif bearish_count > bullish_count:
        overall_bias = "BEARISH"
    else:
        overall_bias = "NEUTRAL"
    
    return {
        "timeframes": mtf_analysis,
        "overall_bias": overall_bias,
        "alignment": bullish_count == len(trends) or bearish_count == len(trends)
    }

def advanced_technical_analysis(symbol: str, interval: str = '1h') -> Dict:
    """Análisis técnico completo con todos los indicadores avanzados."""
    
    df = get_historical_data_extended(symbol, interval=interval, limit=1000)
    
    if df is None or len(df) < 200:
        return {"success": False, "message": f"Datos insuficientes para {symbol} en el intervalo {interval}"}
    
    current_price = float(df['close'].iloc[-1])
    
    market_structure = calculate_market_structure(df)
    sr_zones = calculate_support_resistance_zones(df)
    patterns = detect_chart_patterns(df)
    
    indicators = {}
    indicators['SMA_20'] = talib.SMA(df['close'], 20).iloc[-1]
    indicators['SMA_50'] = talib.SMA(df['close'], 50).iloc[-1]
    indicators['SMA_200'] = talib.SMA(df['close'], 200).iloc[-1]
    indicators['EMA_21'] = talib.EMA(df['close'], 21).iloc[-1]
    indicators['RSI'] = talib.RSI(df['close'], 14).iloc[-1]
    macd, signal, hist = talib.MACD(df['close'])
    indicators['MACD'] = {"macd": macd.iloc[-1], "signal": signal.iloc[-1], "histogram": hist.iloc[-1]}
    bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], 20, 2, 2)
    indicators['Bollinger'] = {
        "upper": bb_upper.iloc[-1], "middle": bb_middle.iloc[-1], "lower": bb_lower.iloc[-1],
        "width": (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / bb_middle.iloc[-1] * 100
    }
    indicators['ATR'] = talib.ATR(df['high'], df['low'], df['close'], 14).iloc[-1]
    indicators['ATR_pct'] = (indicators['ATR'] / current_price) * 100
    indicators['Volume_SMA'] = df['volume'].rolling(20).mean().iloc[-1]
    indicators['Volume_Ratio'] = df['volume'].iloc[-1] / indicators['Volume_SMA']
    
    mtf = perform_multi_timeframe_analysis(symbol, ['15m', '1h', '4h'])
    signals = generate_trading_signals(df, indicators, patterns, sr_zones)
    
    return {
        "success": True,
        "data": {
            "symbol": symbol, "current_price": current_price, "market_structure": market_structure,
            "support_resistance": sr_zones, "patterns": patterns, "indicators": indicators,
            "multi_timeframe": mtf, "signals": signals, "timestamp": df['timestamp'].iloc[-1].isoformat()
        }
    }

def generate_trading_signals(df: pd.DataFrame, indicators: Dict, 
                           patterns: List, sr_zones: Dict) -> Dict:
    """Genera señales de trading basadas en el análisis completo."""
    
    signals = {"bullish": [], "bearish": [], "neutral": []}
    current_price = float(df['close'].iloc[-1])
    
    if indicators['SMA_50'] > indicators['SMA_200']:
        signals["bullish"].append("Golden Cross activo")
    elif indicators['SMA_50'] < indicators['SMA_200']:
        signals["bearish"].append("Death Cross activo")
    
    if indicators['RSI'] < 30:
        signals["bullish"].append("RSI en sobreventa")
    elif indicators['RSI'] > 70:
        signals["bearish"].append("RSI en sobrecompra")
    
    if indicators['MACD']['histogram'] > 0 and indicators['MACD']['macd'] > indicators['MACD']['signal']:
        signals["bullish"].append("MACD bullish crossover")
    elif indicators['MACD']['histogram'] < 0 and indicators['MACD']['macd'] < indicators['MACD']['signal']:
        signals["bearish"].append("MACD bearish crossover")
    
    if current_price < indicators['Bollinger']['lower']:
        signals["bullish"].append("Precio en banda inferior de Bollinger")
    elif current_price > indicators['Bollinger']['upper']:
        signals["bearish"].append("Precio en banda superior de Bollinger")
    
    for pattern in patterns:
        if pattern['signal'] == "Bullish":
            signals["bullish"].append(f"Patrón {pattern['pattern']} detectado")
        else:
            signals["bearish"].append(f"Patrón {pattern['pattern']} detectado")
    
    if sr_zones['support_zones']:
        nearest_support = sr_zones['support_zones'][0]['center']
        if (current_price - nearest_support) / current_price < 0.02:
            signals["bullish"].append(f"Cerca de soporte en ${nearest_support:.2f}")
    
    if sr_zones['resistance_zones']:
        nearest_resistance = sr_zones['resistance_zones'][0]['center']
        if (nearest_resistance - current_price) / current_price < 0.02:
            signals["bearish"].append(f"Cerca de resistencia en ${nearest_resistance:.2f}")
    
    bull_score = len(signals["bullish"])
    bear_score = len(signals["bearish"])
    
    if bull_score > bear_score + 2:
        overall_signal = "STRONG BUY"
    elif bull_score > bear_score:
        overall_signal = "BUY"
    elif bear_score > bull_score + 2:
        overall_signal = "STRONG SELL"
    elif bear_score > bull_score:
        overall_signal = "SELL"
    else:
        overall_signal = "NEUTRAL"
    
    return {
        "signals": signals, "overall": overall_signal,
        "confidence": abs(bull_score - bear_score) / max(bull_score + bear_score, 1) * 100,
        "score": {"bullish": bull_score, "bearish": bear_score}
    }