# Archivo: tools/information_tools.py

import os
import requests
import json
from newsapi import NewsApiClient
from ntscraper import Nitter
from dotenv import load_dotenv
import random
import time

load_dotenv()

# --- CONFIGURACIÓN DE APIS ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
RAPIDAPI_KEYS = [key for i in range(1, 8) if (key := os.getenv(f"RAPID_API_KEY_{i}"))]
current_rapidapi_key_index = 0

# Cargar hosts desde .env
HOSTS = {
    "twitter": os.getenv("RAPIDAPI_HOST_TWITTER"),
    "facebook": os.getenv("RAPIDAPI_HOST_FACEBOOK"),
    "bloomberg": os.getenv("RAPIDAPI_HOST_BLOOMBERG"),
    "reddit": os.getenv("RAPIDAPI_HOST_REDDIT"),
    "wsj": os.getenv("RAPIDAPI_HOST_WSJ"),
    "reuters": os.getenv("RAPIDAPI_HOST_REUTERS")
}

FACEBOOK_BASE_URL = os.getenv("FACEBOOK_BASE_URL")

try:
    newsapi = NewsApiClient(api_key=NEWS_API_KEY)
    print("Cliente de NewsAPI inicializado correctamente.")
except Exception as e:
    newsapi = None; print(f"Error al inicializar NewsAPI: {e}")

if not RAPIDAPI_KEYS:
    print("⚠️ ADVERTENCIA: No se encontraron claves 'RAPID_API_KEY_n'.")

# --- FUNCIÓN CENTRALIZADA PARA LLAMADAS A RAPIDAPI (SIN CAMBIOS) ---
def _make_rapidapi_request(url: str, host: str, params: dict, service_name: str) -> dict:
    global current_rapidapi_key_index
    if not host: return {"success": False, "message": f"Host para {service_name} no configurado en .env"}
    if not RAPIDAPI_KEYS: return {"success": False, "message": f"Claves de API no configuradas."}
    for i in range(len(RAPIDAPI_KEYS)):
        key_index = (current_rapidapi_key_index + i) % len(RAPIDAPI_KEYS)
        current_key = RAPIDAPI_KEYS[key_index]
        headers = {"X-RapidAPI-Key": current_key, "X-RapidAPI-Host": host}
        try:
            print(f"[{service_name}] Petición con clave #{key_index + 1}...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                current_rapidapi_key_index = key_index
                return {"success": True, "data": response.json()}
            elif response.status_code == 429:
                print(f"[{service_name}] ⚠️ Límite excedido en clave #{key_index + 1}. Rotando...")
                continue
            else:
                print(f"[{service_name}] Error {response.status_code} en clave #{key_index + 1}.")
        except requests.exceptions.RequestException as e:
            print(f"[{service_name}] Error de conexión con clave #{key_index + 1}: {e}")
    return {"success": False, "message": f"❌ Todas las claves para {service_name} fallaron."}

# --- HERRAMIENTAS DE INFORMACIÓN INDIVIDUALES ---

def get_news(query: str, page_size: int = 5) -> dict:
    # ... (código existente)
    if not newsapi: return {"success": False, "message": "NewsAPI no disponible."}
    try:
        response = newsapi.get_everything(q=query, language='en', sort_by='relevancy', page_size=page_size)
        if response.get('status') == 'ok' and response.get('totalResults') > 0:
            return {"success": True, "articles": [{"title": a['title'], "source": a['source']['name']} for a in response['articles']]}
    except Exception as e:
        return {"success": False, "message": str(e)}
    return {"success": False, "message": "No se encontraron noticias."}


def get_tweets(query: str, limit: int = 5) -> dict:
    # ... (código existente simplificado)
    return get_tweets_rapidapi(query, limit)

def get_tweets_rapidapi(query: str, limit: int = 5) -> dict:
    url = f"https://{HOSTS['twitter']}/search/search"
    params = {"query": query, "section": "top", "limit": str(limit), "language": "es"}
    result = _make_rapidapi_request(url, HOSTS['twitter'], params, "Twitter")
    if result["success"] and result["data"].get("results"):
        return {"success": True, "tweets": [t["text"] for t in result["data"]["results"] if t.get("text")]}
    return {"success": False, "message": result.get("message", "No se encontraron tweets.")}

def get_facebook_posts(query: str, limit: int = 5) -> dict:
    # ... (código existente)
    if not FACEBOOK_BASE_URL: return {"success": False, "message": "URL de Facebook no configurada."}
    url = f"{FACEBOOK_BASE_URL.rstrip('/')}/search"
    params = {"query": query, "limit": str(limit)}
    result = _make_rapidapi_request(url, HOSTS['facebook'], params, "Facebook")
    if result["success"] and (posts := result["data"].get("results") or result["data"].get("posts")):
        return {"success": True, "posts": [p.get("text", "") for p in posts if p.get("text")]}
    return {"success": False, "message": result.get("message", "No se encontraron posts.")}

# --- NUEVAS FUNCIONES DE NOTICIAS ---

def get_bloomberg_news(limit: int = 5) -> dict:
    """Obtiene audios de tendencia de Bloomberg."""
    url = f"https://{HOSTS['bloomberg']}/media/audios-trending"
    result = _make_rapidapi_request(url, HOSTS['bloomberg'], {}, "Bloomberg")
    if result["success"] and result["data"]:
        return {"success": True, "audios": [item.get("title") for item in result["data"][:limit]]}
    return {"success": False, "message": result.get("message", "No se encontraron audios.")}

def get_reddit_posts(limit: int = 5) -> dict:
    """Obtiene los posts más 'hot' de subreddits de finanzas."""
    posts = []
    for subreddit in ["wallstreetbets", "CryptoCurrency", "investing"]:
        url = f"https://{HOSTS['reddit']}/v1/reddit/subreddit/posts"
        params = {"subreddit": subreddit, "limit": str(limit), "sort": "hot"}
        result = _make_rapidapi_request(url, HOSTS['reddit'], params, f"Reddit ({subreddit})")
        if result["success"] and result["data"].get("data"):
            posts.extend([f"({subreddit}): {p.get('title')}" for p in result["data"]["data"]])
    if posts:
        return {"success": True, "posts": posts}
    return {"success": False, "message": "No se pudieron obtener posts de Reddit."}

def get_wsj_news(query: str = "market", limit: int = 5) -> dict:
    """Busca noticias en el Wall Street Journal."""
    url = f"https://{HOSTS['wsj']}/api/v1/search"
    params = {"query": query, "count": str(limit)}
    result = _make_rapidapi_request(url, HOSTS['wsj'], params, "WSJ")
    if result["success"] and result["data"].get("data"):
        return {"success": True, "articles": [item.get("title") for item in result["data"]["data"]]}
    return {"success": False, "message": result.get("message", "No se encontraron artículos.")}

def get_reuters_news(query: str = "finance", limit: int = 5) -> dict:
    """Busca artículos en Reuters por palabra clave."""
    url = f"https://{HOSTS['reuters']}/articles/get-articles-by-keyword/{query}/0/{limit}"
    result = _make_rapidapi_request(url, HOSTS['reuters'], {}, "Reuters")
    if result["success"] and result["data"].get("articles"):
        return {"success": True, "articles": [item.get("title") for item in result["data"]["articles"]]}
    return {"success": False, "message": result.get("message", "No se encontraron artículos.")}


# --- FUNCIÓN AGREGADORA PRINCIPAL ---

def get_comprehensive_market_briefing_data() -> dict:
    """
    Orquesta la recolección de datos de todas las fuentes para un informe completo.
    """
    print("\n--- INICIANDO INFORME DE INTELIGENCIA DE MERCADO ---")
    
    # Lista de funciones a ejecutar y la clave bajo la cual guardar sus resultados
    data_sources = [
        (get_news, "news_api", "finance, politics, technology"),
        (get_tweets, "twitter", "$BTC, $ETH, market sentiment, economy"),
        (get_facebook_posts, "facebook", "investment opportunities, market crash"),
        (get_bloomberg_news, "bloomberg", None),
        (get_reddit_posts, "reddit", None),
        (get_wsj_news, "wsj", "global market, economy"),
        (get_reuters_news, "reuters", "finance")
    ]
    
    briefing_data = {}
    
    for func, key, query in data_sources:
        print(f"-> Obteniendo datos de: {key.upper()}")
        if query:
            result = func(query)
        else:
            result = func()
            
        if result.get("success"):
            briefing_data[key] = result
        else:
            briefing_data[key] = {"error": result.get("message", "Unknown error")}
            print(f"   ! Falló la obtención de datos para {key.upper()}.")

    print("--- INFORME DE INTELIGENCIA COMPLETADO ---\n")
    return briefing_data