import pandas as pd
import numpy as np

class HistoricalBacktester:
    def __init__(self, optimizer):
        """
        Initialize the backtester with an instance of the optimizer.
        """
        self.optimizer = optimizer
        
    def run(self, historical_data: pd.DataFrame, dt_hours: float = 0.25, chunk_days: int = 7) -> pd.DataFrame:
        """
        Run the optimizer over the historical data. 
        For very large datasets (e.g., 365 days), it's better to chunk it (e.g., week by week)
        to avoid Memory/Timeout issues with the LP solver.
        
        Note: This is a simplified backtester that optimizes chunks independently.
        A true rolling backtester (Milestone 6) would step through time sequentially.
        """
        print(f"Starting backtest over {len(historical_data)} intervals...")
        
        results_list = []
        
        # Calculate chunk size in intervals
        intervals_per_day = int(24 / dt_hours)
        chunk_size = chunk_days * intervals_per_day
        
        current_soc = self.optimizer.params.get('initial_soc_mwh', 0.0)
        
        for i in range(0, len(historical_data), chunk_size):
            chunk = historical_data.iloc[i:i+chunk_size].copy()
            
            # Update initial SOC for this chunk based on the end of the last chunk
            self.optimizer.params['initial_soc_mwh'] = current_soc
            
            # Optimize the chunk
            try:
                chunk_result = self.optimizer.optimize(chunk, dt_hours=dt_hours)
                results_list.append(chunk_result)
                
                # The ending SOC of this chunk becomes the starting SOC of the next
                current_soc = chunk_result['optimal_soc_mwh'].iloc[-1]
            except Exception as e:
                print(f"Optimization failed for chunk starting at {chunk['timestamp'].iloc[0]}: {e}")
                # Fallback to zero actions if optimization fails
                chunk['optimal_charge_mw'] = 0.0
                chunk['optimal_discharge_mw'] = 0.0
                chunk['optimal_reserve_mw'] = 0.0
                chunk['optimal_soc_mwh'] = current_soc
                chunk['energy_revenue'] = 0.0
                chunk['ancillary_revenue'] = 0.0
                chunk['cost'] = 0.0
                chunk['profit'] = 0.0
                results_list.append(chunk)

        # Concatenate all chunk results
        final_results = pd.concat(results_list, ignore_index=True)
        return final_results

    def calculate_metrics(self, results: pd.DataFrame) -> dict:
        """
        Calculate key performance metrics from the backtest results.
        """
        total_energy_revenue = results['energy_revenue'].sum()
        total_ancillary_revenue = results.get('ancillary_revenue', pd.Series([0.0])).sum()
        total_cost = results['cost'].sum()
        net_profit = results['profit'].sum()
        
        metrics = {
            'Total Revenue ($)': total_energy_revenue + total_ancillary_revenue,
            'Energy Revenue ($)': total_energy_revenue,
            'Ancillary Revenue ($)': total_ancillary_revenue,
            'Energy Cost ($)': total_cost,
            'Net Profit ($)': net_profit,
            'Average SOC (MWh)': results['optimal_soc_mwh'].mean()
        }
        
        return metrics

if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../data')))
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../optimizer')))
    
    from synthetic_generator import generate_synthetic_data
    from optimizer import EnergyArbitrageOptimizer
    
    # 1. Generate 30 days of data
    df_market = generate_synthetic_data(days=30)
    
    # 2. Setup battery and optimizer
    battery_params = {
        'power_capacity_mw': 5.0,
        'energy_capacity_mwh': 10.0,
        'charge_efficiency': 0.95,
        'discharge_efficiency': 0.95,
        'initial_soc_mwh': 5.0
    }
    optimizer = EnergyArbitrageOptimizer(battery_params)
    
    # 3. Run backtest
    backtester = HistoricalBacktester(optimizer)
    results = backtester.run(df_market, chunk_days=7)
    
    # 4. Show metrics
    metrics = backtester.calculate_metrics(results)
    print("\n--- Backtest Results (30 Days) ---")
    for k, v in metrics.items():
        print(f"{k}: {v:,.2f}")
