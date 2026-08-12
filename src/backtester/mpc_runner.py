import pandas as pd
from datetime import timedelta
import asyncio
from sqlalchemy import select
from intelligence.explainability import ExplainabilityEngine

class MPCRunner:
    def __init__(self, optimizer, battery_simulator, lookahead_hours: float = 24.0, dt_hours: float = 0.25):
        self.optimizer = optimizer
        self.battery = battery_simulator
        self.lookahead_hours = lookahead_hours
        self.dt_hours = dt_hours
        self.explain_engine = ExplainabilityEngine()
        
    def run_mpc_loop(self, full_market_data: pd.DataFrame):
        """
        Executes the Receding Horizon MPC loop.
        In a real system, this would query the DB at each step. 
        Here, we simulate that strict data isolation by slicing the dataframe.
        """
        print("Starting MPC Receding Horizon Loop...")
        executed_actions = []
        
        # Calculate steps
        total_steps = len(full_market_data)
        lookahead_steps = int(self.lookahead_hours / self.dt_hours)
        
        for t in range(total_steps):
            # 1. Strictly slice ONLY the 24-hour lookahead window from t
            end_idx = min(t + lookahead_steps, total_steps)
            window_data = full_market_data.iloc[t:end_idx].copy()
            
            # 2. Update optimizer's initial SOC to match the actual physical simulator's current SOC
            self.optimizer.params['initial_soc_mwh'] = self.battery.current_soc
            
            # 3. Optimize over the window
            try:
                window_results = self.optimizer.optimize(window_data, dt_hours=self.dt_hours)
                
                # 4. Extract ONLY the action for time t (the immediate next action)
                action_t = window_results.iloc[0]
                command_charge = action_t['optimal_charge_mw']
                command_discharge = action_t['optimal_discharge_mw']
                command_reserve = action_t['optimal_reserve_mw']
                
            except Exception as e:
                print(f"Optimizer failed at step {t}: {e}. Defaulting to safe hold.")
                command_charge = 0.0
                command_discharge = 0.0
                command_reserve = 0.0
                
            # 5. Apply the action to the physical Battery Simulator
            actual_soc = self.battery.step(
                charge_power_mw=command_charge, 
                discharge_power_mw=command_discharge, 
                duration_hours=self.dt_hours
            )
            
            # 6. Generate NLP Explanation
            explanation = self.explain_engine.generate_explanation(
                action=action_t,
                current_soc=self.battery.current_soc,
                max_soc=self.battery.max_soc,
                window_data=window_data
            )
            
            # 7. Record executed action
            current_timestamp = window_data['timestamp'].iloc[0]
            executed_actions.append({
                'timestamp': current_timestamp,
                'charge_mw': command_charge,
                'discharge_mw': command_discharge,
                'reserve_mw': command_reserve,
                'actual_soc_mwh': actual_soc,
                'explanation': explanation
            })
            
            # (In a real system, we would await saving this to TimescaleDB here)
            
            if t % 500 == 0:
                print(f"Processed {t}/{total_steps} steps...")
                
        return pd.DataFrame(executed_actions)
