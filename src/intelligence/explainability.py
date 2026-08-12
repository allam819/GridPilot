import pandas as pd

class ExplainabilityEngine:
    def __init__(self):
        pass

    def generate_explanation(self, 
                             action: pd.Series, 
                             current_soc: float, 
                             max_soc: float, 
                             window_data: pd.DataFrame) -> str:
        """
        Translates a 15-minute dispatch decision into a clear, human-readable justification.
        Relies on simple threshold comparisons vs the 24-hour forecasted average trend.
        """
        # Calculate context averages from the lookahead window
        avg_price = window_data['price_usd_per_mwh'].mean()
        current_price = window_data['price_usd_per_mwh'].iloc[0]
        
        charge_mw = action.get('optimal_charge_mw', 0.0)
        discharge_mw = action.get('optimal_discharge_mw', 0.0)
        reserve_mw = action.get('optimal_reserve_mw', 0.0)
        
        soc_pct = (current_soc / max_soc) * 100 if max_soc > 0 else 0
        
        # Calculate price delta vs average
        if avg_price != 0:
            price_delta_pct = ((current_price - avg_price) / abs(avg_price)) * 100
        else:
            price_delta_pct = 0.0
            
        explanation = ""

        if charge_mw > 0:
            status = "below" if price_delta_pct < 0 else "above"
            explanation = f"Charging {charge_mw:.1f} MW: Current price (${current_price:.2f}) is {abs(price_delta_pct):.0f}% {status} the 24-hour forecasted average. "
            explanation += f"Battery SOC ({soc_pct:.0f}%) has sufficient headroom to store cheap energy."
            
        elif discharge_mw > 0:
            status = "above" if price_delta_pct > 0 else "below"
            explanation = f"Discharging {discharge_mw:.1f} MW: Current price (${current_price:.2f}) is {abs(price_delta_pct):.0f}% {status} the 24-hour forecasted average. "
            explanation += f"Capturing high arbitrage margin with available SOC ({soc_pct:.0f}%)."
            
        elif reserve_mw > 0:
            explanation = f"Holding and providing {reserve_mw:.1f} MW of reserve. "
            explanation += f"Ancillary market offers higher expected value than current energy price (${current_price:.2f})."
            
        else:
            explanation = f"Holding idle: Current price (${current_price:.2f}) does not offer sufficient arbitrage margin or reserve value compared to the 24-hour horizon."
            
        return explanation
