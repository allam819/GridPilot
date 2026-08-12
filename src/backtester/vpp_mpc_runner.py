import pandas as pd
from datetime import timedelta
import asyncio
from intelligence.explainability import ExplainabilityEngine

class VPPMPCRunner:
    def __init__(self, optimizer, battery_simulators: list, lookahead_hours: float = 24.0, dt_hours: float = 0.25):
        self.optimizer = optimizer
        self.batteries = battery_simulators
        self.lookahead_hours = lookahead_hours
        self.dt_hours = dt_hours
        self.explain_engine = ExplainabilityEngine()
        
    def run_mpc_loop(self, full_market_data: pd.DataFrame) -> dict:
        """
        Executes the Receding Horizon MPC loop for all assets simultaneously.
        """
        print("Starting VPP Multi-Asset MPC Receding Horizon Loop...")
        # executed_actions[asset_idx] = list of actions
        executed_actions = [[] for _ in self.batteries]
        
        total_steps = len(full_market_data)
        lookahead_steps = int(self.lookahead_hours / self.dt_hours)
        
        for t in range(total_steps):
            end_idx = min(t + lookahead_steps, total_steps)
            window_data = full_market_data.iloc[t:end_idx].copy()
            
            # Update initial SOC for all batteries in the optimizer
            for a_idx, battery in enumerate(self.batteries):
                self.optimizer.assets[a_idx]['initial_soc_mwh'] = battery.current_soc
                
            try:
                # window_results is a dict: { a_idx: DataFrame }
                window_results = self.optimizer.optimize(window_data, dt_hours=self.dt_hours)
                
                for a_idx, battery in enumerate(self.batteries):
                    action_t = window_results[a_idx].iloc[0]
                    command_charge = action_t['optimal_charge_mw']
                    command_discharge = action_t['optimal_discharge_mw']
                    command_reserve = action_t['optimal_reserve_mw']
                    
                    actual_soc = battery.step(
                        charge_power_mw=command_charge, 
                        discharge_power_mw=command_discharge, 
                        duration_hours=self.dt_hours
                    )
                    
                    # For performance, only generate explanation for node 0 or skip
                    explanation = self.explain_engine.generate_explanation(
                        action=action_t,
                        current_soc=battery.current_soc,
                        max_soc=battery.max_soc,
                        window_data=window_data
                    ) if a_idx == 0 else ""
                    
                    current_timestamp = window_data['timestamp'].iloc[0]
                    executed_actions[a_idx].append({
                        'timestamp': current_timestamp,
                        'charge_mw': command_charge,
                        'discharge_mw': command_discharge,
                        'reserve_mw': command_reserve,
                        'actual_soc_mwh': actual_soc,
                        'explanation': explanation
                    })
            except Exception as e:
                print(f"VPP Optimizer failed at step {t}: {e}. Defaulting to safe hold.")
                for a_idx, battery in enumerate(self.batteries):
                    actual_soc = battery.step(0, 0, self.dt_hours)
                    current_timestamp = window_data['timestamp'].iloc[0]
                    executed_actions[a_idx].append({
                        'timestamp': current_timestamp,
                        'charge_mw': 0.0,
                        'discharge_mw': 0.0,
                        'reserve_mw': 0.0,
                        'actual_soc_mwh': actual_soc,
                        'explanation': "Defaulted to HOLD due to optimization failure."
                    })
                    
            if t % 500 == 0:
                print(f"Processed {t}/{total_steps} steps...")
                
        # Return a dictionary of DataFrames
        return {a_idx: pd.DataFrame(actions) for a_idx, actions in enumerate(executed_actions)}
