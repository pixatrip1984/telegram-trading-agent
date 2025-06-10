# Archivo: deepseek/tools/general_web_query.py

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import re
import time

# --- 1. Reformula el prompt para hacer búsquedas claras ---
def reformulate_prompt(user_query: str) -> str:
    return f"Reformulate this user question for web search clarity: '{user_query}'"

# --- 2. Realiza búsqueda usando DuckDuckGo ---
def search_web_duckduckgo(query: str, max_results: int = 10) -> list:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, safesearch="Moderate", max_results=max_results):
            if r.get("title") and r.get("body") and r.get("href"):
                results.append({
                    "title": r["title"],
                    "snippet": r["body"],
                    "url": r["href"]
                })
            time.sleep(0.2)  # Respetar límites
    return results

# --- 3. Filtra y ordena los fragmentos más relevantes ---
def extract_relevant_snippets(results: list, keywords: list = []) -> str:
    ranked = []
    for r in results:
        score = 0
        combined = (r["title"] + " " + r["snippet"]).lower()
        for kw in keywords:
            if kw.lower() in combined:
                score += 1
        ranked.append((score, r))

    ranked.sort(key=lambda x: -x[0])
    top = [f"<b>{r['title']}</b>\n<i>{r['snippet']}</i>\n<a href=\"{r['url']}\">Fuente</a>\n" for _, r in ranked[:5]]
    return "\n\n".join(top)

# --- 4. Genera una respuesta contextual usando el modelo LLM principal ---
def generate_contextual_response(user_query: str, context_snippets: str, ai_client, model="deepseek/deepseek-chat") -> str:
    prompt = f"""
Eres un experto en análisis de información general. A continuación tienes fragmentos seleccionados de múltiples fuentes. Usa esta información para responder la siguiente pregunta de forma precisa, sin inventar nada.

<b>Pregunta:</b> {user_query}

<b>Fragmentos relevantes:</b>
{context_snippets}

<b>Respuesta:</b>
"""
    response = ai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Eres un agente experto en análisis estratégico y búsqueda web."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# --- 5. Pipeline principal de consulta general ---
def handle_general_web_query(user_query: str, ai_client, keywords: list = []) -> str:
    query = user_query if len(user_query.split()) > 5 else reformulate_prompt(user_query)
    results = search_web_duckduckgo(query)
    if not results:
        return "❌ No se encontraron resultados relevantes en la web."
    context = extract_relevant_snippets(results, keywords)
    return generate_contextual_response(user_query, context, ai_client)

# --- 6. Función opcional para enriquecer informes existentes ---
def enrich_with_general_context(topic: str, ai_client, keywords: list = []) -> dict:
    results = search_web_duckduckgo(topic)
    if not results:
        return {"success": False, "message": "No se encontraron resultados para contexto externo."}
    context = extract_relevant_snippets(results, keywords)
    return {"success": True, "context": context}