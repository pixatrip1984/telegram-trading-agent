# Archivo: tools/asset_mapper.py

import re
from typing import Dict, List, Optional
from fuzzywuzzy import fuzz, process

class AssetMapper:
    """
    Sistema avanzado para mapear, reconocer y normalizar nombres de activos,
    tanto de texto como del historial de conversación.
    """
    
    def __init__(self):
        self.asset_mappings = {
            # Indices Globales
            "s&p 500": "^GSPC", "sp500": "^GSPC", "s&p500": "^GSPC", "sp 500": "^GSPC",
            "nasdaq": "^IXIC", "nasdaq composite": "^IXIC",
            "dow jones": "^DJI", "dow": "^DJI",
            "vix": "^VIX", "indice de volatilidad": "^VIX",
            "nikkei": "^N225", "nikkei 225": "^N225",
            "hang seng": "^HSI",
            "dax": "^GDAXI",
            "ftse 100": "^FTSE",
            
            # Materias Primas
            "oro": "GC=F", "gold": "GC=F",
            "petroleo": "CL=F", "oil": "CL=F", "crudo": "CL=F", "wti": "CL=F",
            "plata": "SI=F", "silver": "SI=F",
            
            # Forex
            "dxy": "DX-Y.NYB", "dolar index": "DX-Y.NYB", "indice dolar": "DX-Y.NYB",

            # Major Cryptocurrencies
            "bitcoin": "BTC", "btc": "BTC",
            "ethereum": "ETH", "eth": "ETH",
            "solana": "SOL", "sol": "SOL",
            "ripple": "XRP", "xrp": "XRP",
            "cardano": "ADA", "ada": "ADA",
            "polygon": "MATIC", "matic": "MATIC",
            "dogecoin": "DOGE", "doge": "DOGE",
            "shiba inu": "SHIB", "shib": "SHIB",
            "avalanche": "AVAX", "avax": "AVAX",
            "chainlink": "LINK", "link": "LINK",
            "polkadot": "DOT", "dot": "DOT",
            "uniswap": "UNI", "uni": "UNI",
            "litecoin": "LTC", "ltc": "LTC",
            "cosmos": "ATOM", "atom": "ATOM",
            "monero": "XMR", "xmr": "XMR",
            "stellar": "XLM", "xlm": "XLM",
            "algorand": "ALGO", "algo": "ALGO",
            "vechain": "VET", "vet": "VET",
            "fantom": "FTM", "ftm": "FTM",
            "hedera": "HBAR", "hbar": "HBAR",
            "tezos": "XTZ", "xtz": "XTZ",
            "eos": "EOS", "eos": "EOS",
            "aave": "AAVE",
            "maker": "MKR", "mkr": "MKR",
            "compound": "COMP", "comp": "COMP",
            "sushi": "SUSHI", "sushiswap": "SUSHI",
            "lido": "LDO", "ldo": "LDO",
            "curve": "CRV", "crv": "CRV",
            "pepe": "PEPE",
            "bonk": "BONK",
            "wif": "WIF", "dogwifhat": "WIF",
            "fetch.ai": "FET", "fet": "FET",
            "render": "RNDR", "rndr": "RNDR",
            "bittensor": "TAO", "tao": "TAO",
            "binance coin": "BNB", "bnb": "BNB",
            "b2usdt": "B2USDT"
        }
        
        # Crear un mapa inverso para buscar nombres a partir de símbolos
        self.symbol_to_names = {}
        for name, symbol in self.asset_mappings.items():
            if symbol not in self.symbol_to_names:
                self.symbol_to_names[symbol] = []
            self.symbol_to_names[symbol].append(name)
    
    def is_traditional_asset(self, symbol: str) -> bool:
        """Verifica si un símbolo corresponde a un activo tradicional (no cripto)."""
        return symbol.startswith('^') or '=F' in symbol or 'DX-Y.NYB' in symbol

    def extract_asset_from_text(self, text: str) -> Optional[str]:
        """Extrae el primer activo que encuentra en un texto usando múltiples métodos."""
        if not text:
            return None
            
        text_lower = text.lower()
        # Ordenar por longitud para encontrar "s&p 500" antes que "s&p"
        sorted_keys = sorted(self.asset_mappings.keys(), key=len, reverse=True)
        
        # 1. Búsqueda exacta de nombres completos
        for name in sorted_keys:
            if re.search(r'\b' + re.escape(name) + r'\b', text_lower):
                return self.asset_mappings[name]
        
        # 2. Búsqueda de tickers/símbolos (ej. $BTC, ETH, SOL)
        symbol_pattern = r'\$?([A-Z0-9]{2,10})\b'
        potential_symbols = re.findall(symbol_pattern, text.upper())
        for symbol in potential_symbols:
            if symbol in self.symbol_to_names or symbol in self.asset_mappings.values():
                # Si es un símbolo válido (BTC, ETH, ^GSPC), lo devolvemos
                return symbol

        # 3. Búsqueda difusa como último recurso
        words = [word for word in re.findall(r'\b\w+\b', text_lower) if len(word) > 2]
        for word in words:
            result = process.extractOne(word, self.asset_mappings.keys(), scorer=fuzz.ratio)
            if result and result[1] > 90: # Umbral de confianza alto para evitar falsos positivos
                return self.asset_mappings[result[0]]
                
        return None
    
    def normalize_to_trading_pair(self, asset: str, base: str = "USDT") -> str:
        """Convierte un símbolo de activo a un par de trading (ej. BTC -> BTCUSDT)."""
        if self.is_traditional_asset(asset):
            return asset # Los activos tradicionales no se emparejan con USDT
        # Limpia el activo de cualquier emparejamiento previo y añade el nuevo
        asset = asset.upper().replace(base, "").replace("USD", "")
        return f"{asset}{base}"

    def get_asset_info(self, symbol: str) -> Dict[str, any]:
        """Obtiene información básica sobre un activo a partir de su símbolo."""
        symbol = symbol.upper()
        if self.is_traditional_asset(symbol):
             return { "symbol": symbol, "names": [k for k, v in self.asset_mappings.items() if v == symbol], "category": "Traditional Market", "is_major": True }
        
        # Lógica para categorizar criptomonedas (simplificada)
        # En un sistema real, esto podría venir de una API como CoinGecko
        major_cryptos = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA"]
        if symbol.replace("USDT", "") in major_cryptos:
            category = "Major Crypto"
            is_major = True
        else:
            category = "Altcoin"
            is_major = False

        return {"symbol": symbol, "names": self.symbol_to_names.get(symbol.replace("USDT", ""), []), "category": category, "is_major": is_major}

    # --- FUNCIÓN NUEVA AÑADIDA ---
    def extract_asset_from_history(self, history: list) -> Optional[str]:
        """
        Busca el último activo mencionado en el historial, revisando desde el mensaje
        más reciente hacia atrás. Esencial para entender el contexto conversacional.
        """
        # Iteramos sobre el historial en orden inverso (del más nuevo al más viejo)
        for message in reversed(history):
            if message.get('role') in ['assistant', 'user']:
                # Usamos nuestra propia función de extracción en el contenido del mensaje
                asset = self.extract_asset_from_text(message['content'])
                if asset:
                    # Si encontramos un activo, lo devolvemos y terminamos la búsqueda
                    print(f"-> Activo '{asset}' recuperado del historial.")
                    # Devolvemos el ticker base para consistencia (ej. BTC en lugar de BTCUSDT)
                    if self.is_traditional_asset(asset):
                        return asset
                    return asset.replace("USDT", "").replace("USD", "")
        return None