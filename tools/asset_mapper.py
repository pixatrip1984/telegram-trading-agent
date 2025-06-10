# Archivo: tools/asset_mapper.py

import re
from typing import Dict, List, Tuple, Optional
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

class AssetMapper:
    """Sistema avanzado de mapeo y reconocimiento de activos crypto."""
    
    def __init__(self):
        # Dataset completo de mapeo nombre -> símbolo
        self.asset_mappings = {
            # Major Cryptocurrencies
            "bitcoin": "BTC", "btc": "BTC", "satoshi": "BTC",
            "ethereum": "ETH", "eth": "ETH", "ether": "ETH",
            "solana": "SOL", "sol": "SOL",
            "ripple": "XRP", "xrp": "XRP",
            "cardano": "ADA", "ada": "ADA",
            "polygon": "MATIC", "matic": "MATIC", "poly": "MATIC",
            "dogecoin": "DOGE", "doge": "DOGE", "shiba": "SHIB",
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
            
            # DeFi
            "aave": "AAVE", "aave": "AAVE",
            "maker": "MKR", "mkr": "MKR",
            "compound": "COMP", "comp": "COMP",
            "sushi": "SUSHI", "sushi": "SUSHI", "sushiswap": "SUSHI",
            "lido": "LDO", "ldo": "LDO",
            "curve": "CRV", "crv": "CRV",
            "pendle": "PENDLE", "pendle": "PENDLE",
            "jupiter": "JUP", "jup": "JUP",
            "pyth": "PYTH", "pyth": "PYTH",
            
            # Meme Coins (Nuevas y populares)
            "pepe": "PEPE", "pepecoin": "PEPE", "pepe coin": "PEPE",
            "bonk": "BONK", "bonk": "BONK",
            "wif": "WIF", "dogwifhat": "WIF", "dog wif hat": "WIF",
            "floki": "FLOKI", "floki inu": "FLOKI",
            "babydoge": "BABYDOGE", "baby doge": "BABYDOGE",
            "chill guy": "CHILLGUY", "chillguy": "CHILLGUY", "just a chill guy": "CHILLGUY",
            "maga": "MAGA", "trump": "MAGA", "donald trump": "MAGA",
            "boden": "BODEN", "joe boden": "BODEN", "biden": "BODEN",
            "dog": "DOG", "dog-go-to-the-moon": "DOG",
            "gme": "GME", "gamestop": "GME",
            "mog": "MOG", "mog coin": "MOG",
            "beer": "BEER", "beercoin": "BEER",
            "andy": "ANDY", "andy": "ANDY",
            "slerf": "SLERF", "slerf": "SLERF",
            
            # AI Tokens
            "fetch": "FET", "fet": "FET", "fetch.ai": "FET",
            "singularitynet": "AGIX", "agix": "AGIX",
            "render": "RNDR", "rndr": "RNDR", "render token": "RNDR",
            "bittensor": "TAO", "tao": "TAO",
            "arkham": "ARKM", "arkm": "ARKM",
            "worldcoin": "WLD", "wld": "WLD",
            "the graph": "GRT", "grt": "GRT",
            "ocean": "OCEAN", "ocean protocol": "OCEAN",
            
            # Gaming & Metaverse
            "decentraland": "MANA", "mana": "MANA",
            "sandbox": "SAND", "sand": "SAND",
            "axie": "AXS", "axs": "AXS", "axie infinity": "AXS",
            "enjin": "ENJ", "enj": "ENJ",
            "theta": "THETA", "theta": "THETA",
            "gala": "GALA", "gala games": "GALA",
            "immutable": "IMX", "imx": "IMX", "immutable x": "IMX",
            "ronin": "RON", "ron": "RON",
            "beam": "BEAM", "beam": "BEAM",
            "notcoin": "NOT", "not": "NOT",
            
            # RWA & DePIN
            "ondo": "ONDO", "ondo finance": "ONDO",
            "chainlink": "LINK", "link": "LINK", # También es RWA
            "filecoin": "FIL", "fil": "FIL",
            "helium": "HNT", "hnt": "HNT",
            "arweave": "AR", "ar": "AR",
            
            # Layer 2 & Scaling
            "arbitrum": "ARB", "arb": "ARB",
            "optimism": "OP", "op": "OP",
            "starknet": "STRK", "strk": "STRK",
            "celestia": "TIA", "tia": "TIA",
            "zk": "ZK", "polyhedra": "ZK",
            "metis": "METIS", "metis": "METIS",
            
            # Nuevos Layer 1
            "sui": "SUI", "sui": "SUI",
            "aptos": "APT", "apt": "APT",
            "sei": "SEI", "sei": "SEI",
            
            # Exchange Tokens
            "binance": "BNB", "bnb": "BNB", "binance coin": "BNB",
            "cronos": "CRO", "cro": "CRO", "crypto.com": "CRO",
            "okb": "OKB", "okb": "OKB",
            "kucoin": "KCS", "kcs": "KCS",
            "wormhole": "W", "w": "W",
            
            # Token de este proyecto
            "swell": "SWELL", "swell network": "SWELL",

            # Common misspellings and variations
            "etherium": "ETH", "etherum": "ETH",
            "doge coin": "DOGE", "dodge": "DOGE",
            "shiba inu": "SHIB", "shib": "SHIB",
            "bitcoins": "BTC", "bit coin": "BTC"
        }
        
        # Crear índice inverso para búsqueda rápida
        self.symbol_to_names = {}
        for name, symbol in self.asset_mappings.items():
            if symbol not in self.symbol_to_names:
                self.symbol_to_names[symbol] = []
            self.symbol_to_names[symbol].append(name)
    
    def extract_asset_from_text(self, text: str) -> Optional[str]:
        """
        Extrae el activo mencionado en el texto usando múltiples estrategias.
        Retorna el símbolo del activo o None si no encuentra ninguno.
        """
        text_lower = text.lower()
        
        # 1. Búsqueda por nombre completo o parcial (mejorada para evitar falsos positivos)
        best_match = None
        best_len = 0
        
        # Priorizar coincidencias más largas para evitar que "sol" coincida con "solana" en medio de otra palabra
        sorted_keys = sorted(self.asset_mappings.keys(), key=len, reverse=True)
        for name in sorted_keys:
            if re.search(r'\b' + re.escape(name) + r'\b', text_lower):
                return self.asset_mappings[name]
        
        # 2. Búsqueda de símbolos (case-insensitive)
        symbol_pattern = r'\b([A-Z]{2,10})\b'
        potential_symbols = re.findall(symbol_pattern, text.upper())
        
        for symbol in potential_symbols:
            if symbol in self.symbol_to_names:
                return symbol
        
        # 3. Búsqueda de patrones especiales (con $)
        dollar_pattern = r'\$([A-Za-z]{2,10})'
        dollar_matches = re.findall(dollar_pattern, text)
        for match in dollar_matches:
            symbol = match.upper()
            if symbol in self.symbol_to_names:
                return symbol
            if symbol.lower() in self.asset_mappings:
                return self.asset_mappings[symbol.lower()]

        # 4. Búsqueda fuzzy como último recurso
        words = re.findall(r'\b\w+\b', text_lower)
        for word in words:
            # Encontrar el mejor match para la palabra actual
            result = process.extractOne(word, self.asset_mappings.keys(), scorer=fuzz.ratio)
            if result and result[1] > 90: # Score de confianza alto
                return self.asset_mappings[result[0]]

        return None
    
    def normalize_to_trading_pair(self, asset: str, base: str = "USDT") -> str:
        """Convierte un activo a un par de trading completo."""
        if not asset:
            return None
        
        asset = asset.upper()
        base = base.upper()
        
        if asset.endswith(base):
            return asset
        
        if asset == base:
            return None
        
        return f"{asset}{base}"
    
    def get_asset_info(self, symbol: str) -> Dict[str, any]:
        """Retorna información adicional sobre el activo."""
        symbol = symbol.upper()
        
        info = {
            "symbol": symbol,
            "names": self.symbol_to_names.get(symbol, []),
            "category": self._categorize_asset(symbol),
            "is_stablecoin": symbol in ["USDT", "USDC", "DAI", "BUSD"],
            "is_meme": self._categorize_asset(symbol) == "Meme",
            "is_major": symbol in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA"]
        }
        
        return info
    
    def _categorize_asset(self, symbol: str) -> str:
        """Categoriza el activo."""
        categories = {
            "DeFi": ["UNI", "AAVE", "MKR", "LDO", "CRV", "PENDLE", "JUP", "PYTH", "SUSHI"],
            "Layer 1": ["BTC", "ETH", "SOL", "ADA", "AVAX", "DOT", "ATOM", "SUI", "APT", "SEI"],
            "Layer 2": ["MATIC", "ARB", "OP", "STRK", "ZK", "METIS"],
            "Meme": ["DOGE", "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "MAGA", "BODEN", "DOG", "GME", "MOG", "BEER", "ANDY", "SLERF"],
            "Gaming": ["AXS", "SAND", "MANA", "GALA", "IMX", "RON", "BEAM", "NOT"],
            "AI": ["FET", "AGIX", "RNDR", "TAO", "ARKM", "WLD", "GRT", "OCEAN"],
            "Exchange": ["BNB", "CRO", "OKB", "KCS", "W"],
            "Stablecoin": ["USDT", "USDC", "DAI", "BUSD"],
            "Privacy": ["XMR", "ZEC", "DASH"],
            "RWA/DePIN": ["ONDO", "LINK", "FIL", "HNT", "AR"],
            "Other": ["SWELL", "XLM", "VET", "FTM", "HBAR", "XTZ"]
        }
        
        for category, symbols in categories.items():
            if symbol in symbols:
                return category
        
        return "Other"
    
    def suggest_related_assets(self, symbol: str, limit: int = 5) -> List[str]:
        """Sugiere activos relacionados basándose en la categoría."""
        info = self.get_asset_info(symbol)
        category = info["category"]
        
        # Mapa inverso de categorías
        category_map = {cat: syms for cat, syms in self._get_all_categories().items()}

        if category in category_map:
            related = [asset for asset in category_map[category] if asset != symbol]
            return related[:limit]
        
        return []

    def _get_all_categories(self) -> Dict:
        # Helper para tener el mapa de categorías en un solo lugar
        return {
            "DeFi": ["UNI", "AAVE", "MKR", "LDO", "CRV", "PENDLE", "JUP", "PYTH", "SUSHI"],
            "Layer 1": ["BTC", "ETH", "SOL", "ADA", "AVAX", "DOT", "ATOM", "SUI", "APT", "SEI"],
            "Layer 2": ["MATIC", "ARB", "OP", "STRK", "ZK", "METIS"],
            "Meme": ["DOGE", "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "MAGA", "BODEN", "DOG", "GME", "MOG", "BEER", "ANDY", "SLERF"],
            "Gaming": ["AXS", "SAND", "MANA", "GALA", "IMX", "RON", "BEAM", "NOT"],
            "AI": ["FET", "AGIX", "RNDR", "TAO", "ARKM", "WLD", "GRT", "OCEAN"],
            "Exchange": ["BNB", "CRO", "OKB", "KCS", "W"],
            "Stablecoin": ["USDT", "USDC", "DAI", "BUSD"],
            "Privacy": ["XMR", "ZEC", "DASH"],
            "RWA/DePIN": ["ONDO", "LINK", "FIL", "HNT", "AR"],
            "Other": ["SWELL", "XLM", "VET", "FTM", "HBAR", "XTZ"]
        }