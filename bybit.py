import os
from dotenv import load_dotenv
from pybit.unified_trading import HTTP

load_dotenv()

bybit_key = os.getenv("PRUEBA_API_KEY")
bybit_secret = os.getenv("PRUEBA_API_SECRET")

if not bybit_key or not bybit_secret:
    print("¡ERROR CRÍTICO! Las variables no se están cargando desde .env.")
else:
    print("Variables cargadas. Conectando a Bybit Testnet...")
    
    try:
        session = HTTP(
            testnet=True,
            api_key=bybit_key,
            api_secret=bybit_secret,
        )
        
        print("\n--- NUEVA ESTRATEGIA: PROBANDO EL MERCADO DE DERIVADOS (CONTRATOS PERPETUOS) ---")
        print("El mercado Spot de la Testnet parece tener un bug. Ahora intentaremos con un contrato lineal.")
        
        # --- PARÁMETROS PARA UN CONTRATO PERPETUO LINEAL ---
        order_params = {
            "category": "linear",     # ¡¡¡EL CAMBIO MÁS IMPORTANTE!!!
            "symbol": "BTCUSDT",      # Volvemos a BTC, es el contrato más líquido.
            "side": "Buy",            # "Buy" para abrir una posición larga.
            "orderType": "Market",    # Orden de mercado.
            "qty": "0.001"            # Para derivados, la cantidad SÍ se especifica en la moneda base (BTC). 0.001 es un tamaño de contrato estándar.
        }
        
        print(f"\nColocando orden en el mercado '{order_params['category']}' para {order_params['qty']} {order_params['symbol']}...")

        order_result = session.place_order(**order_params)
        
        print("\n##########################################")
        print("    ¡¡¡¡ VICTORIA FINAL !!!!")
        print("    ¡¡¡ ORDEN EJECUTADA CON ÉXITO !!!")
        print("##########################################")
        print("\nLa orden en el mercado de DERIVADOS funcionó. El problema era el mercado Spot.")
        print("Respuesta de la API:")
        print(order_result)

    except Exception as e:
        print(f"\nOcurrió un error: {e}")