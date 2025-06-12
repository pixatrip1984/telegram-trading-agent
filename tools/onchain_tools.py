# Archivo: tools/onchain_tools.py

import requests
import pandas as pd
from typing import Dict, List, Optional
import time
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
import traceback

load_dotenv()

class FreeWhaleTracker:
    """Tracker de ballenas usando APIs gratuitas, con manejo de errores y fallbacks."""

    def __init__(self):
        self.apis = {
            "etherscan": "https://api.etherscan.io/api",
            "coingecko": "https://api.coingecko.com/api/v3",
            "blockchair": "https://api.blockchair.com"
        }
        self.etherscan_key = os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")
        self.whale_addresses = {
            "ethereum": {
                "binance_hot_1": "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",
                "binance_hot_2": "0x28c6c06298d514db089934071355e5743bf21d60",
                "binance_cold_1": "0x564286362092d8e7936f0549571a803b203aaced",
                "coinbase_1": "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
                "kraken_1": "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
            },
            "bitcoin": {
                "binance_cold_1": "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
                "binance_cold_2": "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",
                "coinbase_cold": "36n4EMJrgW88aGJnYaHZJH7JjSF3jw2nxp",
            }
        }

    def _get_real_price(self, coin_id: str) -> float:
        """Obtiene el precio actual de una criptomoneda usando CoinGecko, con fallback."""
        fallback_prices = {"ethereum": 3400, "bitcoin": 67000}
        try:
            url = f"{self.apis['coingecko']}/simple/price"
            params = {"ids": coin_id, "vs_currencies": "usd"}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if coin_id in data and 'usd' in data[coin_id]:
                price = data[coin_id]["usd"]
                print(f"  {coin_id.upper()} Price: ${price:,.2f}")
                return price
            raise ValueError(f"Respuesta inesperada de la API de precios: {data}")
        except Exception as e:
            print(f"  ❌ Error getting {coin_id} price: {e}. Usando precio de fallback.")
            return fallback_prices.get(coin_id, 1)

    def get_real_eth_whale_activity(self) -> Dict:
        """Obtiene actividad REAL de ballenas en Ethereum desde Etherscan."""
        print("🔍 Obteniendo datos REALES de ballenas Ethereum...")
        large_transfers = []
        eth_price = self._get_real_price("ethereum")
        
        for whale_name, address in self.whale_addresses["ethereum"].items():
            try:
                params = { "module": "account", "action": "txlist", "address": address, "page": 1, "offset": 20, "sort": "desc", "apikey": self.etherscan_key }
                response = requests.get(self.apis["etherscan"], params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "1" and data.get("result"):
                        for tx in data["result"]:
                            tx_time = datetime.fromtimestamp(int(tx["timeStamp"]))
                            if tx_time > datetime.now() - timedelta(days=3):
                                value_eth = int(tx["value"]) / 1e18
                                if value_eth > 100: # Umbral para transferencias ETH significativas
                                    large_transfers.append({ "hash": tx["hash"], "whale_name": whale_name, "value_eth": round(value_eth, 2), "value_usd": round(value_eth * eth_price, 2), "direction": "inflow" if tx["to"].lower() == address.lower() else "outflow", "whale_type": self._classify_whale_size(value_eth * eth_price) })
            except Exception as e:
                print(f"    ❌ Error revisando {whale_name}: {e}")
        
        print(f"  📊 Total transferencias ETH significativas encontradas: {len(large_transfers)}")
        analysis = self._analyze_transfers(large_transfers)
        return { "success": True, "data_source": "Etherscan API", "large_transfers": sorted(large_transfers, key=lambda x: x["value_usd"], reverse=True), "analysis": analysis, "price_used": eth_price }

    def get_real_btc_whale_activity(self) -> Dict:
        """Obtiene actividad REAL de ballenas en Bitcoin desde Blockchair."""
        print("🔍 Obteniendo datos REALES de ballenas Bitcoin desde Blockchair...")
        btc_price = self._get_real_price("bitcoin")
        min_value_usd = 2_000_000 # Umbral de $2M USD
        since_date = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
        
        url = f"{self.apis['blockchair']}/bitcoin/transactions"
        params = { "limit": 50, "s": "time(desc)", "q": f"time({since_date}..),output_total_usd({min_value_usd}..)" }
        
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            transactions = data.get('data', [])
            print(f"  📡 Blockchair encontró {len(transactions)} transacciones grandes recientes.")
            
            if not transactions:
                return {"success": True, "note": "No se detectó actividad de ballenas de BTC en las últimas 72 horas.", "large_transfers": [], "analysis": {}}
            
            large_transfers = []
            for tx in transactions:
                is_inflow = any(output.get('is_exchange') for output in tx.get('outputs', []))
                large_transfers.append({ "hash": tx["hash"], "value_usd": round(tx["output_total_usd"], 2), "direction": "inflow" if is_inflow else "outflow", "whale_type": self._classify_whale_size(tx["output_total_usd"]) })
            
            analysis = self._analyze_transfers(large_transfers)
            return { "success": True, "data_source": "Blockchair API", "large_transfers": sorted(large_transfers, key=lambda x: x["value_usd"], reverse=True), "analysis": analysis, "price_used": btc_price }

        except Exception as e:
            print(f"  ❌ Error obteniendo datos reales de BTC: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_transfers(self, transfers: List[Dict]) -> Dict:
        """Analiza una lista de transferencias para calcular flujos y sentimiento."""
        if not transfers: return {}
        df = pd.DataFrame(transfers)
        
        inflows = df[df['direction'] == 'inflow']['value_usd'].sum()
        outflows = df[df['direction'] == 'outflow']['value_usd'].sum()
        net_flow = outflows - inflows
        
        sentiment = "neutral"
        if net_flow > 1_000_000: sentiment = "bullish"
        elif net_flow < -1_000_000: sentiment = "bearish"
        
        return {
            "exchange_inflows": round(inflows), 
            "exchange_outflows": round(outflows), 
            "net_flow": round(net_flow), 
            "total_volume_usd": round(df['value_usd'].sum()), 
            "sentiment_indicator": sentiment
        }
    
    def _classify_whale_size(self, value_usd: float) -> str:
        if value_usd >= 50_000_000: return "🐋 MEGA WHALE"
        if value_usd >= 10_000_000: return "🐋 LARGE WHALE"
        if value_usd >= 1_000_000: return "🐳 WHALE"
        return "🐟 LARGE FISH"

class OnChainMetrics:
    def get_fear_greed_index(self) -> Dict:
        try:
            r = requests.get("https://api.alternative.me/fng/", timeout=5).json()['data'][0]
            return {"success": True, "value": int(r['value']), "classification": r['value_classification']}
        except Exception as e:
            print(f"  ❌ Error obteniendo Fear & Greed Index: {e}")
            return {"success": False}
    
    def get_social_sentiment_metrics(self, coin_id: str) -> Dict:
        try:
            r = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}", timeout=10).json()
            score = 50 + r.get("sentiment_votes_up_percentage", 50) - r.get("sentiment_votes_down_percentage", 50)
            return {"success": True, "sentiment_score": min(100, max(0, score))}
        except Exception as e:
            print(f"  ❌ Error obteniendo Social Sentiment: {e}")
            return {"success": False}

def analyze_whale_activity(asset: str = "ethereum") -> Dict:
    tracker, metrics = FreeWhaleTracker(), OnChainMetrics()
    try:
        if asset.lower() in ["bitcoin", "btc"]:
            whale_data = tracker.get_real_btc_whale_activity()
        elif asset.lower() in ["ethereum", "eth"]:
            whale_data = tracker.get_real_eth_whale_activity()
        else:
            return {"success": False, "error": f"Asset {asset} no soportado."}
        
        if not whale_data.get("success"):
            return whale_data

        fear_greed = metrics.get_fear_greed_index()
        coin_id = "bitcoin" if asset.lower() in ["btc", "bitcoin"] else "ethereum"
        social_sentiment = metrics.get_social_sentiment_metrics(coin_id)
        
        overall_sentiment = _calculate_overall_sentiment(whale_data, fear_greed, social_sentiment)
        
        return {
            "success": True,
            "data": {
                "asset": asset.upper(),
                "whale_activity": whale_data,
                "fear_greed_index": fear_greed,
                "social_sentiment": social_sentiment,
                "overall_sentiment": overall_sentiment,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def _calculate_overall_sentiment(whale_data, fear_greed, social) -> Dict:
    sentiment_score, confidence, factors = 50, 40, []
    
    if whale_data.get("success"):
        analysis = whale_data.get("analysis", {})
        whale_sentiment = analysis.get("sentiment_indicator", "neutral")
        total_volume = analysis.get("total_volume_usd", 0)

        if whale_sentiment == "bullish":
            sentiment_score += 20; factors.append("Ballenas retirando fondos de exchanges (Bullish)")
        elif whale_sentiment == "bearish":
            sentiment_score -= 20; factors.append("Ballenas depositando fondos en exchanges (Bearish)")
        
        if total_volume > 50_000_000: confidence += 20; factors.append("Volumen de ballenas masivo.")
        elif total_volume > 10_000_000: confidence += 10
    
    if fear_greed.get("success"):
        fg_value = fear_greed.get("value", 50)
        if fg_value <= 30: sentiment_score += 15; factors.append("Mercado en Miedo Extremo")
        elif fg_value >= 70: sentiment_score -= 15; factors.append("Mercado en Codicia Extrema")
        confidence += 15
    
    if social.get("success"):
        sentiment_score += (social.get("sentiment_score", 50) - 50) / 5
    
    classification = "Neutral"
    if sentiment_score >= 70: classification = "Fuertemente Bullish"
    elif sentiment_score >= 55: classification = "Bullish"
    elif sentiment_score <= 30: classification = "Fuertemente Bearish"
    elif sentiment_score <= 45: classification = "Bearish"
    
    return {
        "sentiment_score": min(100, max(0, int(sentiment_score))),
        "classification": classification,
        "contributing_factors": factors,
        "confidence": min(100, confidence)
    }