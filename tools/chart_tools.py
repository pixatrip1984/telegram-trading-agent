import os
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tools.analysis_tools import get_historical_data_extended
from matplotlib.colors import LinearSegmentedColormap

def generate_candlestick_chart(symbol, interval='1h', title=None, support_levels=None, resistance_levels=None):
    """
    Genera un gráfico de velas con niveles de soporte/resistencia y heatmap de liquidación
    
    Args:
        symbol (str): Símbolo del activo (ej: 'BTCUSDT')
        interval (str): Intervalo de tiempo (ej: '1h', '4h', '1d')
        title (str): Título personalizado para el gráfico
        support_levels (list): Lista de niveles de soporte
        resistance_levels (list): Lista de niveles de resistencia
        
    Returns:
        str: Ruta al archivo de imagen generado
    """
    # Obtener datos históricos
    data = get_historical_data_extended(symbol, interval=interval, limit=100)
    if data is None or data.empty:
        return None

    # Crear mapa de colores para el heatmap de liquidación
    colors = ["#4B0082", "#0000FF", "#00FF00", "#FFFF00"]  # Morado -> Azul -> Verde -> Amarillo
    cmap = LinearSegmentedColormap.from_list("liquidation_heatmap", colors)
    
    # Configuración del estilo
    style = mpf.make_mpf_style(
        base_mpf_style='charles',
        marketcolors=mpf.make_marketcolors(
            up='#2ECC71',  # Verde para velas alcistas
            down='#E74C3C',  # Rojo para velas bajistas
            wick={'up':'#2ECC71', 'down':'#E74C3C'},
            edge={'up':'#2ECC71', 'down':'#E74C3C'},
            volume='in'
        ),
        facecolor='#1E1E2D',  # Fondo oscuro
        edgecolor='#2D2D44',
        figcolor='#1E1E2D',
        gridcolor='#2D2D44',
        gridstyle='--',
        rc={
            'axes.labelcolor': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white',
            'font.size': 9
        }
    )
    
    # Crear figura
    fig, axes = mpf.plot(
        data,
        type='candle',
        style=style,
        title=title or f"{symbol} - {interval}",
        ylabel=f"Precio ({symbol})",
        volume=True,
        figratio=(12, 8),
        figscale=1.2,
        returnfig=True,
        show_nontrading=False,
        warn_too_much_data=10000
    )
    
    ax_main = axes[0]
    ax_vol = axes[2]
    
    # Agregar niveles de soporte y resistencia
    if support_levels:
        for level in support_levels:
            ax_main.axhline(y=level, color='#2ECC71', linestyle='-', alpha=0.7, linewidth=1.5)
            ax_main.annotate(f'Soporte: {level:.4f}', 
                             (data.index[-10], level), 
                             xytext=(0, 10), 
                             textcoords='offset points',
                             color='#2ECC71',
                             fontsize=9,
                             ha='right')
    
    if resistance_levels:
        for level in resistance_levels:
            ax_main.axhline(y=level, color='#E74C3C', linestyle='-', alpha=0.7, linewidth=1.5)
            ax_main.annotate(f'Resistencia: {level:.4f}', 
                             (data.index[-10], level), 
                             xytext=(0, -15), 
                             textcoords='offset points',
                             color='#E74C3C',
                             fontsize=9,
                             ha='right')
    
    # Simular heatmap de liquidación (datos reales requerirían API de liquidaciones)
    # Esto es un placeholder hasta que implementemos datos reales
    if len(data) > 20:
        price_range = np.linspace(data['low'].min(), data['high'].max(), 100)
        time_range = np.arange(len(data))
        xx, yy = np.meshgrid(time_range, price_range)
        
        # Crear datos simulados para el heatmap
        z = np.sin(xx/5) * np.cos(yy/100)  # Función de ejemplo
        
        heatmap = ax_main.pcolormesh(
            xx, yy, z,
            cmap=cmap,
            alpha=0.15,
            shading='auto'
        )
        
        # Agregar barra de color para el heatmap
        cbar = fig.colorbar(heatmap, ax=ax_main, pad=0.02)
        cbar.set_label('Intensidad de Liquidación', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        cbar.outline.set_edgecolor('#2D2D44')
        plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='white')
    
    # Configurar ejes
    ax_main.set_facecolor('#1E1E2D')
    ax_vol.set_facecolor('#1E1E2D')
    
    # Guardar gráfico
    chart_dir = os.path.join(os.getcwd(), 'charts')
    os.makedirs(chart_dir, exist_ok=True)
    chart_path = os.path.join(chart_dir, f"{symbol}_{interval}.png")
    fig.savefig(chart_path, bbox_inches='tight', dpi=150)
    plt.close(fig)
    
    return chart_path
