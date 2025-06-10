# Archivo: tools/ecosystem_tools.py

from typing import Dict, List, Any
from .bybit_tools import get_price

class EcosystemMapper:
    """Mapea relaciones entre tokens y ecosistemas crypto."""
    
    def __init__(self):
        # Mapa simplificado y claro de ecosistemas
        self.ecosystems = {
            "ETHEREUM": {
                "parent": "ETH",
                "layer2": ["MATIC", "ARB", "OP"],
                "defi": ["UNI", "AAVE", "COMP", "MKR"],
                "memes": ["SHIB", "PEPE"]
            },
            "SOLANA": {
                "parent": "SOL",
                "defi": ["RAY", "ORCA"],
                "memes": ["BONK", "WIF", "CHILLGUY"]
            },
            "BNB": {
                "parent": "BNB",
                "defi": ["CAKE"],
                "memes": ["BABYDOGE"]
            }
        }
        
        self.categories = {
            "AI": ["FET", "AGIX", "RNDR", "TAO"],
            "GAMING": ["AXS", "SAND", "MANA", "GALA"],
            "DEFI": ["UNI", "AAVE", "SUSHI", "CRV"],
            "LAYER2": ["MATIC", "ARB", "OP"],
            "PRIVACY": ["XMR", "ZEC", "DASH"]
        }

    def find_token_ecosystem(self, token: str) -> Dict[str, Any]:
        """Encuentra el ecosistema de un token."""
        token = token.upper()
        result = {
            "token": token,
            "ecosystem": None,
            "category": None,
            "related": []
        }
        
        # Buscar en ecosistemas
        for eco_name, eco_data in self.ecosystems.items():
            all_tokens = [eco_data.get("parent", "")] + \
                        eco_data.get("layer2", []) + \
                        eco_data.get("defi", []) + \
                        eco_data.get("memes", [])
            
            if token in all_tokens:
                result["ecosystem"] = eco_name
                result["related"] = [t for t in all_tokens if t != token][:10]
                break
        
        # Buscar en categorías
        for cat_name, tokens in self.categories.items():
            if token in tokens:
                result["category"] = cat_name
                break
                
        return result

    def predict_contagion(self, token: str, event: str = "pump") -> List[Dict]:
        """Predice qué tokens se moverán con el token dado."""
        token = token.upper()
        ecosystem = self.find_token_ecosystem(token)
        predictions = []
        
        # Si tiene tokens relacionados en su ecosistema
        if ecosystem["related"]:
            for related in ecosystem["related"][:5]:
                predictions.append({
                    "token": related,
                    "impact": "HIGH",
                    "timing": "0-4 horas"
                })
        
        # Si está en una categoría
        if ecosystem["category"]:
            category_tokens = self.categories.get(ecosystem["category"], [])
            for cat_token in category_tokens:
                if cat_token != token and cat_token not in ecosystem["related"]:
                    predictions.append({
                        "token": cat_token,
                        "impact": "MEDIUM",
                        "timing": "4-24 horas"
                    })
                    
        return predictions[:10]  # Máximo 10 predicciones

# Función principal para el dispatcher
def analyze_ecosystem(query: str, analysis_type: str = "map") -> Dict[str, Any]:
    """
    Análisis de ecosistemas crypto.
    Tipos: map, contagion
    """
    mapper = EcosystemMapper()
    
    try:
        if analysis_type == "map":
            return {"success": True, "data": mapper.find_token_ecosystem(query)}
            
        elif analysis_type == "contagion":
            # Formato: "TOKEN" o "TOKEN,pump"
            parts = query.split(",")
            token = parts[0].strip()
            event = parts[1].strip() if len(parts) > 1 else "pump"
            
            predictions = mapper.predict_contagion(token, event)
            return {
                "success": True, 
                "data": {
                    "trigger": token,
                    "event": event,
                    "predictions": predictions
                }
            }
            
        else:
            return {"success": False, "message": "Tipo de análisis no válido"}
            
    except Exception as e:
        return {"success": False, "message": str(e)}