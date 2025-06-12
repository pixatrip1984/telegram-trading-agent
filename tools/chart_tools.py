# Archivo: tools/chart_tools.py

import os
import mplfinance as mpf
import matplotlib.pyplot as plt
import pandas as pd
import traceback
import talib
from tools.analysis_tools import get_historical_data_extended

def generate_candlestick_chart(
    symbol: str, 
    interval: str = '1h', 
    title: str = None, 
    support_levels: list = None, 
    resistance_levels: list = None
) -> str:
    """
    Genera un gráfico de velas con niveles de S/R, Medias Móviles y Bandas de Bollinger.
    """
    print(f"-> Generando gráfico avanzado para {symbol} en {interval}...")
    # Pedimos más datos para que los indicadores se calculen bien
    data = get_historical_data_extended(symbol, interval=interval, limit=200)
    if data is None or data.empty or not isinstance(data.index, pd.DatetimeIndex):
        print(f"  ❌ Datos insuficientes o mal formateados para el gráfico de {symbol}.")
        return None

    # Tomamos las últimas 100 velas para que el gráfico no esté muy apretado
    plot_data = data.tail(100)

    mc = mpf.make_marketcolors(
        up='#2ECC71', down='#E74C3C',
        wick={'up':'#2ECC71', 'down':'#E74C3C'},
        edge='inherit', volume='inherit'
    )
    style = mpf.make_mpf_style(
        base_mpf_style='charles',
        marketcolors=mc,
        facecolor='#1E1E2D', figcolor='#1E1E2D',
        gridcolor='#2D2D44', gridstyle='--',
        rc={'axes.labelcolor': 'white', 'xtick.color': 'white', 'ytick.color': 'white'}
    )
    
    # --- Añadir Indicadores al Gráfico ---
    plots_to_add = []
    
    # 1. Medias Móviles (SMA 20 y 50)
    sma20 = talib.SMA(data['close'], timeperiod=20)
    sma50 = talib.SMA(data['close'], timeperiod=50)
    plots_to_add.append(mpf.make_addplot(sma20.tail(100), color='cyan', width=0.7))
    plots_to_add.append(mpf.make_addplot(sma50.tail(100), color='yellow', width=0.7))

    # 2. Bandas de Bollinger
    upper, middle, lower = talib.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
    plots_to_add.append(mpf.make_addplot(upper.tail(100), color='gray', width=0.6, linestyle='--'))
    plots_to_add.append(mpf.make_addplot(lower.tail(100), color='gray', width=0.6, linestyle='--'))

    # 3. Niveles de Soporte y Resistencia
    if support_levels:
        for level in support_levels:
            line = pd.Series([float(level)] * len(plot_data), index=plot_data.index)
            plots_to_add.append(mpf.make_addplot(line, color='#3498DB', width=1.0, linestyle='-.')) # Azul para soporte
            
    if resistance_levels:
        for level in resistance_levels:
            line = pd.Series([float(level)] * len(plot_data), index=plot_data.index)
            plots_to_add.append(mpf.make_addplot(line, color='#F39C12', width=1.0, linestyle='-.')) # Naranja para resistencia
        
    try:
        chart_dir = os.path.join(os.getcwd(), 'charts')
        os.makedirs(chart_dir, exist_ok=True)
        chart_path = os.path.join(chart_dir, f"{symbol.replace('/', '_')}_{interval}_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}.png")

        mpf.plot(
            plot_data, # Graficamos solo las últimas 100 velas
            type='candle',
            style=style,
            title=title or f"\nAnálisis Técnico de {symbol} - {interval}",
            ylabel='Precio (USD)',
            volume=True,
            figratio=(16, 9),
            figscale=1.5, # Hacemos el gráfico un poco más grande
            addplot=plots_to_add if plots_to_add else None,
            savefig=chart_path,
            show_nontrading=False
        )
        
        print(f"  ✅ Gráfico avanzado guardado en: {chart_path}")
        return chart_path

    except Exception as e:
        print(f"  ❌ Error al generar el gráfico con mplfinance: {e}")
        traceback.print_exc()
        return None