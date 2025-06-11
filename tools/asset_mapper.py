# Archivo: tools/asset_mapper.py

import re
from typing import Dict, List, Optional
from fuzzywuzzy import fuzz, process

class AssetMapper:
    """Sistema avanzado de mapeo y reconocimiento de activos."""
    
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
            "b2usdt": "B2USDT" # Añadido por tu log de error
        }
        
        self.symbol_to_names = {}
        for name, symbol in self.asset_mappings.items():
            if symbol not in self.symbol_to_names:
                self.symbol_to_names[symbol] = []
            self.symbol_to_names[symbol].append(name)
    
    def is_traditional_asset(self, symbol: str) -> bool:
        """Verifica si un símbolo corresponde a un activo tradicional (no cripto)."""
        return symbol.startswith('^') or '=F' in symbol or 'DX-Y.NYB' in symbol

    def extract_asset_from_text(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        sorted_keys = sorted(self.asset_mappings.keys(), key=len, reverse=True)
        for name in sorted_keys:
            if re.search(r'\b' + re.escape(name) + r'\b', text_lower):
                return self.asset_mappings[name]
        
        symbol_pattern = r'\$?([A-Z0-9]{2,10})\b'
        potential_symbols = re.findall(symbol_pattern, text.upper())
        for symbol in potential_symbols:
            if symbol in self.symbol_to_names:
                return symbol

        words = [word for word in re.findall(r'\b\w+\b', text_lower) if len(word) > 2]
        for word in words:
            result = process.extractOne(word, self.asset_mappings.keys(), scorer=fuzz.ratio)
            if result and result[1] > 90:
                return self.asset_mappings[result[0]]
        return None
    
    def normalize_to_trading_pair(self, asset: str, base: str = "USDT") -> str:
        if self.is_traditional_asset(asset):
            return asset
        asset = asset.upper().replace(base, "")
        return f"{asset}{base}"

    def get_asset_info(self, symbol: str) -> Dict[str, any]:
        symbol = symbol.upper()
        if self.is_traditional_asset(symbol):
             return { "symbol": symbol, "names": [k for k, v in self.asset_mappings.items() if v == symbol], "category": "Traditional Market", "is_major": True }
        # ... (resto de la lógica de categorización de cripto) ...
        return {"symbol": symbol, "names": [], "category": "Crypto"}