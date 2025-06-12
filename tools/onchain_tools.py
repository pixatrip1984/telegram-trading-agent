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
    """Tracker de ballenas usando SOLO APIs gratuitas"""

    def __init__(self):
        # APIs 100% gratuitas
        self.apis = {
            "etherscan": "https://api.etherscan.io/api",
            "coingecko": "https://api.coingecko.com/api/v3",
            "alternative": "https://api.alternative.me",
            "blockchair": "https://api.blockchair.com",
            "btc_com": "https://chain.api.btc.com/v3"
        }

        # Claves API
        self.etherscan_key = os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")

        # Direcciones REALES de ballenas (información pública)
        self.whale_addresses = {
            "ethereum": {
                "binance_hot_1": "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",
                "binance_hot_2": "0x28c6c06298d514db089934071355e5743bf21d60",
                "binance_cold_1": "0x564286362092d8e7936f0549571a803b203aaced",
                "coinbase_1": "0x71660c4005ba85c37ccec55d0c4493e66fe775d3",
                "coinbase_2": "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43",
                "kraken_1": "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
                "kraken_2": "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13",
                "huobi_1": "0x18709e89bd3d3cfcbb5b44e5e8cc3b4d5c0cf9a2",
                "okx_1": "0x98ec059dc3adfbdd63429454aeb0c990fba4a128"
            },
            "bitcoin": {
                "binance_cold_1": "1NDyJtNTjmwk5xPNhjgAMu4HDHigtobu1s",
                "binance_cold_2": "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",
                "coinbase_cold": "36n4EMJrgW88aGJnYaHZJH7JjSF3jw2nxp",
                "unknown_whale_1": "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF",
                "unknown_whale_2": "1LdRcdxfbSnmCYYNdeYpUnztiYzVfBEQeC"
            }
        }

    def _get_real_price(self, coin_id: str) -> float:
        """Obtiene el precio actual de una criptomoneda usando CoinGecko"""
        try:
            url = f"{self.apis['coingecko']}/simple/price"
            params = {"ids": coin_id, "vs_currencies": "usd"}
            response = requests.get(url, params=params, timeout=5)
            price = response.json()[coin_id]["usd"]
            print(f"  {coin_id.upper()} Price: ${price:,.2f}")
            return price
        except Exception as e:
            print(f"  Error getting {coin_id} price: {e}")
            fallback_prices = {"ethereum": 3400, "bitcoin": 67000}
            return fallback_prices.get(coin_id, 1)

    def get_real_eth_whale_activity(self, min_value_eth: float = 10) -> Dict:
        """Obtiene actividad REAL de ballenas en Ethereum"""
        try:
            print("🔍 Obteniendo datos REALES de ballenas Ethereum...")
            large_transfers = []
            eth_price = self._get_real_price("ethereum")
            
            for whale_name, address in self.whale_addresses["ethereum"].items():
                try:
                    params = {
                        "module": "account", "action": "txlist", "address": address,
                        "page": 1, "offset": 50, "sort": "desc",
                        "apikey": self.etherscan_key
                    }
                    response = requests.get(self.apis["etherscan"], params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "1" and data.get("result"):
                            print(f"    ✅ {len(data['result'])} transacciones encontradas para {whale_name}")
                            for tx in data["result"][:20]:
                                tx_time = datetime.fromtimestamp(int(tx["timeStamp"]))
                                hours_ago = (datetime.now() - tx_time).total_seconds() / 3600
                                if hours_ago <= 72:
                                    value_eth = int(tx["value"]) / 1e18
                                    value_usd = value_eth * eth_price
                                    if value_eth >= 5 or value_usd >= 10000:
                                        is_inflow = tx["to"].lower() == address.lower()
                                        
                                        large_transfers.append({
                                            "hash": tx["hash"],
                                            "whale_name": whale_name,
                                            "whale_address": address,
                                            "from_address": tx["from"],
                                            "to_address": tx["to"],
                                            "value_eth": round(value_eth, 4),
                                            "value_usd": round(value_usd, 2),
                                            "timestamp": tx_time.isoformat(),
                                            "hours_ago": round(hours_ago, 1),
                                            "direction": "inflow" if is_inflow else "outflow",
                                            "whale_type": self._classify_whale_size(value_usd)
                                        })
                except Exception as e:
                    print(f"    ❌ Error revisando {whale_name}: {e}")
            
            print(f"  📊 Total transferencias significativas encontradas: {len(large_transfers)}")
            
            if not large_transfers:
                print("  -> No se encontraron transferencias grandes, buscando actividad reciente...")
                return self._get_any_recent_activity()
            
            analysis = self._analyze_real_eth_transfers(large_transfers)
            
            return {
                "success": True,
                "data_source": "Etherscan API (REAL DATA)",
                "total_transfers": len(large_transfers),
                "large_transfers": sorted(large_transfers, key=lambda x: x["value_usd"], reverse=True),
                "analysis": analysis,
                "eth_price_used": eth_price,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"Error CRÍTICO en get_real_eth_whale_activity: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _get_any_recent_activity(self) -> Dict:
        """Fallback: obtiene CUALQUIER actividad reciente si no hay transferencias grandes"""
        try:
            print("  -> Ejecutando fallback _get_any_recent_activity...")
            recent_activity = []
            eth_price = self._get_real_price("ethereum")
            
            if not self.whale_addresses["ethereum"]:
                return {"success": True, "note": "No hay direcciones de ballenas de ETH para revisar.", "large_transfers": [], "analysis": {}}
            
            whale_name, address = next(iter(self.whale_addresses["ethereum"].items()))
            
            params = {
                "module": "account", "action": "txlist", "address": address,
                "page": 1, "offset": 10, "sort": "desc",
                "apikey": self.etherscan_key
            }
            response = requests.get(self.apis["etherscan"], params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "1" and data.get("result"):
                    for tx in data["result"]:
                        value_eth = int(tx["value"]) / 1e18
                        if value_eth > 0.5:
                            value_usd = value_eth * eth_price
                            is_inflow = tx["to"].lower() == address.lower()
                            recent_activity.append({
                                "hash": tx["hash"],
                                "whale_name": whale_name,
                                "value_usd": round(value_usd, 2),
                                "direction": "inflow" if is_inflow else "outflow",
                                "whale_type": self._classify_whale_size(value_usd)
                            })
            
            if recent_activity:
                analysis = self._analyze_real_eth_transfers(recent_activity)
                return {
                    "success": True,
                    "note": "Mostrando actividad reciente debido a baja actividad de ballenas.",
                    "large_transfers": recent_activity,
                    "analysis": analysis,
                    "total_transfers": len(recent_activity),
                    "timestamp": datetime.now().isoformat()
                }
            
            return {"success": True, "note": "Periodo de muy baja actividad on-chain.", "large_transfers": [], "analysis": {}}
        
        except Exception as e:
            print(f"Error CRÍTICO en _get_any_recent_activity: {e}")
            traceback.print_exc()
            return {"success": False, "error": f"Error en fallback: {str(e)}"}
    
    def get_real_btc_whale_activity(self, min_value_btc: float = 10) -> Dict:
        """Obtiene actividad REAL de ballenas en Bitcoin"""
        try:
            print("🔍 Obteniendo datos REALES de ballenas Bitcoin desde Blockchair...")
            
            btc_price = self._get_real_price("bitcoin")
            min_value_usd = min_value_btc * btc_price
            
            since_date = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
            
            url = f"{self.apis['blockchair']}/bitcoin/transactions"
            params = {
                "limit": 50,
                "s": "time(desc)",
                "q": f"time({since_date}..),output_total_usd({min_value_usd}..)"
            }
            
            print(f"-> Petición a Blockchair con params: {params}")
            
            response = requests.get(url, params=params, timeout=20)
            
            if response.status_code != 200:
                print(f"  ❌ Error en la API de Blockchair: Status {response.status_code}, {response.text}")
                return {"success": False, "error": f"La API de datos on-chain (Blockchair) devolvió un error {response.status_code}. No se pueden obtener los datos."}
            
            data = response.json()
            transactions = data.get('data', [])
            print(f"  📡 Blockchair encontró {len(transactions)} transacciones grandes recientes.")
            
            if not transactions:
                return {"success": True, "note": "No se detectó actividad de ballenas de BTC en las últimas 72 horas.", "large_transfers": [], "analysis": {}}
            
            large_transfers = []
            for tx in transactions:
                tx_time = datetime.fromisoformat(tx["time"].replace("Z", "+00:00"))
                hours_ago = (datetime.now(tx_time.tzinfo) - tx_time).total_seconds() / 3600
                
                is_inflow_to_exchange = any(output.get('is_exchange') for output in tx.get('outputs', []))
                
                large_transfers.append({
                    "hash": tx["hash"],
                    "value_btc": round(tx["output_total"] / 1e8, 4),
                    "value_usd": round(tx["output_total_usd"], 2),
                    "timestamp": tx["time"],
                    "hours_ago": round(hours_ago, 1),
                    "fee_usd": round(tx["fee_usd"], 2),
                    "direction": "inflow" if is_inflow_to_exchange else "outflow",
                    "whale_type": self._classify_whale_size(tx["output_total_usd"]),
                    "data_source": "Blockchair"
                })
            
            print(f"  📊 Total transferencias BTC procesadas: {len(large_transfers)}")
            
            analysis = self._analyze_real_btc_transfers(large_transfers)
            
            return {
                "success": True,
                "data_source": "Blockchair API (REAL DATA)",
                "total_transfers": len(large_transfers),
                "large_transfers": sorted(large_transfers, key=lambda x: x["value_usd"], reverse=True),
                "analysis": analysis,
                "btc_price_used": btc_price,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error obteniendo datos reales de BTC: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _analyze_real_eth_transfers(self, transfers: List[Dict]) -> Dict:
        if not transfers: return {}
        df = pd.DataFrame(transfers)
        inflows = df[df['direction'] == 'inflow']['value_usd'].sum()
        outflows = df[df['direction'] == 'outflow']['value_usd'].sum()
        net_flow = outflows - inflows
        sentiment = "bullish" if net_flow > 1_000_000 else "bearish" if net_flow < -1_000_000 else "neutral"
        return {"exchange_inflows": round(inflows), "exchange_outflows": round(outflows), "net_flow": round(net_flow), "total_volume_usd": round(df['value_usd'].sum()), "sentiment_indicator": sentiment}
    
    def _analyze_real_btc_transfers(self, transfers: List[Dict]) -> Dict:
        """
        Analiza las transferencias de BTC para calcular flujos de entrada/salida a exchanges.
        Esta función ahora replica la lógica de _analyze_real_eth_transfers para consistencia.
        """
        if not transfers: 
            return {}
            
        df = pd.DataFrame(transfers)
        
        inflows = df[df['direction'] == 'inflow']['value_usd'].sum()
        outflows = df[df['direction'] == 'outflow']['value_usd'].sum()
        
        net_flow = outflows - inflows
        
        if net_flow > 1_000_000:
            sentiment = "bullish"
        elif net_flow < -1_000_000:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
            
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
    def __init__(self):
        self.whale_tracker = FreeWhaleTracker()
    
    def get_fear_greed_index(self) -> Dict:
        try:
            r = requests.get("https://api.alternative.me/fng/", timeout=5).json()['data'][0]
            return {"success": True, "value": int(r['value']), "classification": r['value_classification']}
        except: return {"success": False}
    
    def get_social_sentiment_metrics(self, coin_id: str) -> Dict:
        try:
            r = requests.get(f"https://api.coingecko.com/api/v3/coins/{coin_id}", timeout=10).json()
            community = r.get("community_data", {})
            score = 50
            if community.get("twitter_followers", 0) > 1_000_000: score += 10
            return {"success": True, "sentiment_score": min(100, score)}
        except: return {"success": False}

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
            return whale_data # Devolver el error de la API si lo hubo

        # --- LÍNEA CORREGIDA ---
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
                "overall_sentiment": overall_sentiment
            }
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def _calculate_overall_sentiment(whale_data, fear_greed, social) -> Dict:
    """Calcula sentimiento general con lógica de confianza mejorada."""
    sentiment_score, confidence, factors = 50, 40, []
    
    if whale_data.get("success"):
        analysis = whale_data.get("analysis", {})
        whale_sentiment = analysis.get("sentiment_indicator", "neutral")
        total_volume = analysis.get("total_volume_usd", 0)

        if whale_sentiment == "bullish":
            sentiment_score += 20
            factors.append("Ballenas retirando fondos de exchanges (Bullish)")
            confidence += 20
        elif whale_sentiment == "bearish":
            sentiment_score -= 20
            factors.append("Ballenas depositando fondos en exchanges (Bearish)")
            confidence += 20
        else:
            factors.append("Flujo neto de ballenas equilibrado.")

        if total_volume > 50_000_000:
            confidence += 20
            factors.append("Volumen de ballenas masivo.")
        elif total_volume > 10_000_000:
            confidence += 10
            factors.append("Volumen de ballenas significativo.")
    
    if fear_greed.get("success"):
        fg_value = fear_greed.get("value", 50)
        if fg_value <= 30:
            sentiment_score += 15
            factors.append("Mercado en Miedo Extremo")
            confidence += 15
        elif fg_value >= 70:
            sentiment_score -= 15
            factors.append("Mercado en Codicia Extrema")
            confidence += 15
    
    if social.get("success") and social.get("sentiment_score", 50) > 65:
        sentiment_score += 10
        factors.append("Sentimiento social positivo.")
    
    classification = "Neutral"
    if sentiment_score >= 70: classification = "Fuertemente Bullish"
    elif sentiment_score >= 55: classification = "Bullish"
    elif sentiment_score <= 30: classification = "Fuertemente Bearish"
    elif sentiment_score <= 45: classification = "Bearish"
    
    return {
        "sentiment_score": min(100, max(0, sentiment_score)),
        "classification": classification,
        "contributing_factors": factors,
        "confidence": min(100, confidence)
    }