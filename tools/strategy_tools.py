# Archivo: tools/strategy_tools_v2.py

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import talib
from datetime import datetime, timedelta

class AdvancedStrategyGenerator:
    """Generador de estrategias adaptativo para cualquier capital y timeframe."""
    
    def __init__(self):
        self.risk_multipliers = {
            "low": 0.01,      # 1% riesgo por trade
            "medium": 0.02,   # 2% riesgo
            "high": 0.05,     # 5% riesgo
            "degen": 0.10     # 10% riesgo - YOLO mode
        }
        
        self.leverage_limits = {
            "low": 3,
            "medium": 10,
            "high": 20,
            "degen": 50
        }
        
        self.timeframe_configs = {
            "1m": {"hold_time": "5-15 min", "targets": [0.1, 0.2, 0.3]},
            "5m": {"hold_time": "15-60 min", "targets": [0.2, 0.4, 0.6]},
            "15m": {"hold_time": "1-4 hours", "targets": [0.5, 1.0, 1.5]},
            "1h": {"hold_time": "4-24 hours", "targets": [1.0, 2.0, 3.0]},
            "4h": {"hold_time": "1-3 days", "targets": [2.0, 4.0, 6.0]},
            "1d": {"hold_time": "3-14 days", "targets": [5.0, 10.0, 15.0]}
        }
    
    def calculate_position_size(self, capital: float, entry: float, stop_loss: float, 
                              risk_level: str = "medium") -> Dict:
        """Calcula el tamaño de posición basado en gestión de riesgo."""
        risk_amount = capital * self.risk_multipliers[risk_level]
        price_risk = abs(entry - stop_loss) / entry
        
        # Posición base sin apalancamiento
        position_size_usd = risk_amount / price_risk
        
        # Aplicar límites según capital
        if capital < 100:
            max_position = capital * 0.8  # 80% máximo para cuentas pequeñas
        elif capital < 1000:
            max_position = capital * 2    # 2x máximo
        else:
            max_position = capital * self.leverage_limits[risk_level]
        
        position_size_usd = min(position_size_usd, max_position)
        
        # Calcular apalancamiento real necesario
        leverage_needed = position_size_usd / capital
        leverage_used = min(leverage_needed, self.leverage_limits[risk_level])
        
        return {
            "position_size_usd": round(position_size_usd, 2),
            "leverage": round(leverage_used, 1),
            "risk_amount": round(risk_amount, 2),
            "risk_percentage": round((risk_amount / capital) * 100, 2),
            "coins": round(position_size_usd / entry, 8)
        }
    
    def generate_entry_zones(self, current_price: float, trend: str, 
                           volatility: float) -> List[Dict]:
        """Genera zonas de entrada escalonadas."""
        entries = []
        
        if trend == "bullish":
            # Entradas en retrocesos para tendencia alcista
            retracement_levels = [0.5, 1.0, 1.5]  # % de retroceso
        else:
            # Entradas en rebotes para tendencia bajista
            retracement_levels = [-0.5, -1.0, -1.5]
        
        for i, level in enumerate(retracement_levels):
            entry_price = current_price * (1 - level/100)
            allocation = [30, 40, 30][i]  # Distribución 30-40-30
            
            entries.append({
                "price": round(entry_price, 4),
                "allocation_pct": allocation,
                "condition": f"Toque y rebote en ${entry_price:.4f}"
            })
        
        return entries
    
    def calculate_targets(self, entry_price: float, timeframe: str, 
                         trend_strength: float) -> List[Dict]:
        """Calcula objetivos de precio dinámicos."""
        tf_config = self.timeframe_configs.get(timeframe, self.timeframe_configs["1h"])
        base_targets = tf_config["targets"]
        
        # Ajustar targets según fuerza de tendencia
        multiplier = 1.0 + (trend_strength / 10)  # trend_strength de -10 a 10
        
        targets = []
        remaining_position = 100
        
        for i, base_target in enumerate(base_targets):
            target_pct = base_target * multiplier
            target_price = entry_price * (1 + target_pct/100)
            
            # Distribución: 40%, 30%, 30%
            exit_pct = [40, 30, 30][i]
            
            targets.append({
                "price": round(target_price, 4),
                "gain_pct": round(target_pct, 2),
                "exit_allocation": exit_pct,
                "remaining_position": remaining_position - exit_pct
            })
            
            remaining_position -= exit_pct
        
        return targets
    
    def generate_grid_parameters(self, price_data: pd.DataFrame, capital: float) -> Dict:
        """Genera parámetros óptimos para Grid Trading."""
        current_price = float(price_data['close'].iloc[-1])
        
        # Análisis de volatilidad y rango
        high_low_pct = ((price_data['high'] - price_data['low']) / price_data['low']).mean() * 100
        
        # ATR para volatilidad
        atr = talib.ATR(price_data['high'], price_data['low'], price_data['close'])
        atr_pct = (atr.iloc[-1] / current_price) * 100
        
        # Determinar número de grids según capital
        if capital < 100:
            num_grids = 5
        elif capital < 500:
            num_grids = 10
        elif capital < 2000:
            num_grids = 20
        else:
            num_grids = min(int(capital / 100), 50)
        
        # Rango del grid basado en volatilidad
        if atr_pct < 1:
            range_multiplier = 2
        elif atr_pct < 3:
            range_multiplier = 3
        else:
            range_multiplier = 4
        
        upper_price = current_price * (1 + (atr_pct * range_multiplier) / 100)
        lower_price = current_price * (1 - (atr_pct * range_multiplier) / 100)
        
        return {
            "type": "Neutral Grid",
            "upper_limit": round(upper_price, 4),
            "lower_limit": round(lower_price, 4),
            "num_grids": num_grids,
            "investment_per_grid": round(capital / num_grids, 2),
            "expected_profit_per_grid": round((upper_price - lower_price) / num_grids / current_price * 100, 3),
            "optimal_market": "Rango lateral con volatilidad",
            "stop_loss": round(lower_price * 0.95, 4)
        }
    
    def generate_dca_strategy(self, current_price: float, capital: float, 
                            timeframe: str = "1d") -> Dict:
        """Genera estrategia de Dollar Cost Averaging inteligente."""
        # Niveles de compra progresivos
        dca_levels = []
        remaining_capital = capital
        
        # Distribución: 20%, 25%, 30%, 25%
        allocations = [0.20, 0.25, 0.30, 0.25]
        price_drops = [0, -5, -10, -15]  # % de caída para cada nivel
        
        for i, (alloc, drop) in enumerate(zip(allocations, price_drops)):
            dca_price = current_price * (1 + drop/100)
            dca_amount = capital * alloc
            
            dca_levels.append({
                "level": i + 1,
                "price": round(dca_price, 4),
                "amount_usd": round(dca_amount, 2),
                "condition": f"Precio cae a ${dca_price:.4f} (-{abs(drop)}%)" if drop < 0 else "Entrada inicial"
            })
        
        # Calcular precio promedio esperado
        total_coins = sum(level["amount_usd"] / level["price"] for level in dca_levels)
        avg_price = capital / total_coins
        
        return {
            "type": "DCA Inteligente",
            "levels": dca_levels,
            "average_price": round(avg_price, 4),
            "profit_targets": [
                {"price": round(avg_price * 1.10, 4), "action": "Recuperar 50%"},
                {"price": round(avg_price * 1.20, 4), "action": "Recuperar 30%"},
                {"price": round(avg_price * 1.30, 4), "action": "Cerrar posición"}
            ],
            "max_investment": capital,
            "strategy": "Comprar en caídas, vender en recuperación"
        }
    
    def generate_martingale_recovery(self, initial_loss: float, capital: float,
                                   win_rate: float = 0.6) -> Dict:
        """Genera plan de recuperación tipo Martingala modificado."""
        recovery_plan = []
        accumulated_loss = initial_loss
        current_bet = initial_loss * 0.5  # Empezar con 50% de la pérdida
        max_trades = 10
        
        for i in range(max_trades):
            # Limitar apuesta al 20% del capital restante
            max_bet = (capital - accumulated_loss) * 0.2
            current_bet = min(current_bet, max_bet)
            
            if current_bet < 1:  # Mínimo $1
                break
            
            # Calcular ganancia necesaria para cubrir pérdidas
            required_gain_pct = (accumulated_loss / current_bet) * 100
            
            recovery_plan.append({
                "trade": i + 1,
                "bet_size": round(current_bet, 2),
                "required_gain": round(required_gain_pct, 1),
                "accumulated_risk": round(accumulated_loss + current_bet, 2),
                "success_probability": round(win_rate ** (i + 1) * 100, 1)
            })
            
            if win_rate > 0.5:  # Si ganamos más del 50%
                accumulated_loss = 0  # Reset en caso de ganar
                break
            else:
                accumulated_loss += current_bet
                current_bet *= 1.5  # Incremento del 50%
        
        return {
            "type": "Recuperación Martingala Modificada",
            "initial_loss": initial_loss,
            "recovery_trades": recovery_plan,
            "max_risk": round(sum(t["bet_size"] for t in recovery_plan), 2),
            "break_even_probability": round(win_rate * 100, 1),
            "warning": "Alto riesgo - Solo para traders experimentados"
        }

def generate_advanced_trading_strategy(scores: Dict, tech_data: Dict, 
                                     multi_tf_data: Dict, user_profile: Dict) -> Dict:
    """Genera estrategia completa adaptada al perfil del usuario."""
    
    generator = AdvancedStrategyGenerator()
    
    # Extraer parámetros
    capital = user_profile.get("capital", 100)
    risk_level = user_profile.get("risk_level", "medium")
    strategy_type = user_profile.get("strategy_type", "directional")
    timeframe = user_profile.get("timeframe", "1h")
    
    # Datos técnicos
    current_price = tech_data.get("current_price", 0)
    support = tech_data.get("key_levels", {}).get("support", [current_price * 0.95])[0]
    resistance = tech_data.get("key_levels", {}).get("resistance", [current_price * 1.05])[0]
    
    # Score consolidado
    total_score = (
        scores.get("technical_analysis", 0) * 0.5 +
        scores.get("news", 0) * 0.2 +
        scores.get("sentiment", 0) * 0.15 +
        scores.get("facebook", 0) * 0.15
    )
    
    # Determinar dirección
    if total_score >= 2:
        direction = "LONG"
        trend = "bullish"
        entry_zone = current_price * 0.99  # Entrada en retroceso
        stop_loss = support * 0.98
    elif total_score <= -2:
        direction = "SHORT"
        trend = "bearish"
        entry_zone = current_price * 1.01  # Entrada en rebote
        stop_loss = resistance * 1.02
    else:
        direction = "NEUTRAL"
        trend = "ranging"
        entry_zone = current_price
        stop_loss = current_price * 0.97
    
    # Calcular volatilidad para ajustes
    if timeframe in multi_tf_data and len(multi_tf_data[timeframe]) > 20:
        tf_data = multi_tf_data[timeframe]
        volatility = tf_data['close'].pct_change().std() * 100
    else:
        volatility = 2.0  # Default 2%
    
    strategy = {
        "direction": direction,
        "confidence_score": round(abs(total_score), 2),
        "market_regime": scores.get("market_regime", "trending")
    }
    
    # Generar estrategia según tipo
    if strategy_type == "directional" or direction != "NEUTRAL":
        # Estrategia direccional clásica
        position_calc = generator.calculate_position_size(
            capital, entry_zone, stop_loss, risk_level
        )
        
        entry_zones = generator.generate_entry_zones(
            current_price, trend, volatility
        )
        
        targets = generator.calculate_targets(
            entry_zone, timeframe, total_score
        )
        
        strategy.update({
            "type": "Direccional",
            "position_sizing": position_calc,
            "entry_zones": entry_zones,
            "stop_loss": round(stop_loss, 4),
            "targets": targets,
            "risk_reward_ratio": round(
                (targets[0]["price"] - entry_zone) / (entry_zone - stop_loss), 2
            ),
            "holding_period": generator.timeframe_configs[timeframe]["hold_time"]
        })
    
    elif strategy_type == "grid":
        # Grid Trading
        grid_data = None
        for tf, data in multi_tf_data.items():
            if len(data) > 0:
                grid_data = data
                break
        
        if grid_data is not None:
            grid_params = generator.generate_grid_parameters(grid_data, capital)
            strategy.update({
                "type": "Grid Trading",
                "grid_setup": grid_params,
                "best_scenario": "Mercado lateral con volatilidad del 2-5% diario"
            })
    
    elif strategy_type == "dca":
        # Dollar Cost Averaging
        dca_strategy = generator.generate_dca_strategy(
            current_price, capital, timeframe
        )
        strategy.update({
            "type": "DCA Strategy",
            "dca_plan": dca_strategy,
            "time_horizon": "Medio-largo plazo"
        })
    
    elif strategy_type == "martingale":
        # Martingala para recuperación
        # Asumir pérdida inicial del 10% para ejemplo
        initial_loss = capital * 0.1
        recovery_plan = generator.generate_martingale_recovery(
            initial_loss, capital, win_rate=0.65
        )
        strategy.update({
            "type": "Martingale Recovery",
            "recovery_strategy": recovery_plan,
            "risk_warning": "⚠️ Estrategia de alto riesgo"
        })
    
    else:  # mixed o default
        # Estrategia mixta: Direccional + Grid de seguridad
        position_calc = generator.calculate_position_size(
            capital * 0.6,  # 60% para direccional
            entry_zone, stop_loss, risk_level
        )
        
        # Grid con 40% restante
        if len(multi_tf_data) > 0:
            grid_data = list(multi_tf_data.values())[0]
            grid_params = generator.generate_grid_parameters(
                grid_data, capital * 0.4
            )
        else:
            grid_params = None
        
        strategy.update({
            "type": "Estrategia Mixta",
            "directional_component": {
                "allocation": "60%",
                "position": position_calc,
                "entry": round(entry_zone, 4),
                "stop_loss": round(stop_loss, 4),
                "target": round(entry_zone * 1.03, 4)
            },
            "grid_component": {
                "allocation": "40%",
                "setup": grid_params
            } if grid_params else None,
            "advantage": "Ganancias direccionales + ingresos consistentes del grid"
        })
    
    # Agregar plan de contingencia
    strategy["contingency_plan"] = generate_contingency_plan(
        capital, risk_level, current_price
    )
    
    # Métricas de riesgo
    strategy["risk_metrics"] = calculate_risk_metrics(
        strategy, capital, volatility
    )
    
    return strategy

def generate_contingency_plan(capital: float, risk_level: str, 
                             current_price: float) -> Dict:
    """Genera plan B en caso de que la operación vaya mal."""
    
    max_loss_pct = {
        "low": 5,
        "medium": 10,
        "high": 20,
        "degen": 30
    }[risk_level]
    
    max_loss = capital * (max_loss_pct / 100)
    
    return {
        "max_loss_allowed": round(max_loss, 2),
        "recovery_options": [
            {
                "scenario": "Pérdida del 5%",
                "action": "Doblar posición en soporte fuerte",
                "requirement": f"Confirmación en ${current_price * 0.95:.2f}"
            },
            {
                "scenario": "Pérdida del 10%",
                "action": "Iniciar Grid Trading para recuperación",
                "requirement": "Cambio a mercado lateral"
            },
            {
                "scenario": f"Pérdida del {max_loss_pct}%",
                "action": "Cerrar todas las posiciones",
                "requirement": "Preservar capital restante"
            }
        ],
        "hedging_option": {
            "instrument": "Short en futuros",
            "size": "20% de la posición principal",
            "trigger": "Ruptura de soporte clave"
        }
    }

def calculate_risk_metrics(strategy: Dict, capital: float, 
                          volatility: float) -> Dict:
    """Calcula métricas de riesgo avanzadas."""
    
    # Value at Risk (VaR) simplificado
    var_95 = capital * (volatility / 100) * 1.645  # 95% confianza
    
    # Maximum Drawdown esperado
    if strategy.get("type") == "Grid Trading":
        expected_dd = capital * 0.15  # Grids tienen menos DD
    elif strategy.get("type") == "Martingale Recovery":
        expected_dd = capital * 0.40  # Alto riesgo
    else:
        expected_dd = capital * 0.20  # Direccional estándar
    
    # Ratio de Kelly simplificado
    win_rate = 0.55  # Asumiendo 55% win rate con buen análisis
    avg_win = volatility * 2  # Ganancia promedio
    avg_loss = volatility  # Pérdida promedio
    
    kelly_pct = ((win_rate * avg_win) - ((1 - win_rate) * avg_loss)) / avg_win
    
    return {
        "value_at_risk_95": round(var_95, 2),
        "expected_max_drawdown": round(expected_dd, 2),
        "kelly_criterion": round(kelly_pct * 100, 1),
        "recommended_allocation": round(min(kelly_pct * capital, capital * 0.25), 2),
        "break_even_trades": calculate_breakeven_trades(strategy),
        "profit_factor": round(win_rate * avg_win / ((1-win_rate) * avg_loss), 2)
    }

def calculate_breakeven_trades(strategy: Dict) -> int:
    """Calcula cuántos trades ganadores se necesitan para breakeven."""
    if strategy.get("type") == "Martingale Recovery":
        return 1  # Solo necesita 1 trade ganador
    elif strategy.get("type") == "Grid Trading":
        return 3  # Varios pequeños profits
    else:
        # Basado en risk/reward ratio
        rr_ratio = strategy.get("risk_reward_ratio", 2)
        return max(1, int(1 / (rr_ratio / (1 + rr_ratio))))

# Función helper para análisis avanzado con indicadores
def calculate_advanced_indicators(df: pd.DataFrame) -> Dict:
    """Calcula indicadores técnicos avanzados."""
    indicators = {}
    
    # Medias móviles
    indicators['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
    indicators['SMA_50'] = talib.SMA(df['close'], timeperiod=50)
    indicators['EMA_12'] = talib.EMA(df['close'], timeperiod=12)
    indicators['EMA_26'] = talib.EMA(df['close'], timeperiod=26)
    
    # Momentum
    indicators['RSI'] = talib.RSI(df['close'], timeperiod=14)
    indicators['MACD'], indicators['MACD_signal'], indicators['MACD_hist'] = talib.MACD(df['close'])
    indicators['STOCH_K'], indicators['STOCH_D'] = talib.STOCH(df['high'], df['low'], df['close'])
    
    # Volatilidad
    indicators['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    indicators['BB_upper'], indicators['BB_middle'], indicators['BB_lower'] = talib.BBANDS(df['close'])
    
    # Volumen
    indicators['OBV'] = talib.OBV(df['close'], df['volume'])
    indicators['VWAP'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
    
    # Patrones
    indicators['DOJI'] = talib.CDLDOJI(df['open'], df['high'], df['low'], df['close'])
    indicators['HAMMER'] = talib.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])
    indicators['ENGULFING'] = talib.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
    
    return indicators