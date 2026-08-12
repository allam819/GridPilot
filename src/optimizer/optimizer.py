import pandas as pd
from ortools.linear_solver import pywraplp

class EnergyArbitrageOptimizer:
    def __init__(self, battery_params: dict):
        """
        :param battery_params: dict containing:
            - power_capacity_mw
            - energy_capacity_mwh
            - charge_efficiency
            - discharge_efficiency
            - min_soc_mwh
            - max_soc_mwh
            - initial_soc_mwh
        """
        self.params = battery_params

    def optimize(self, market_data: pd.DataFrame, dt_hours: float = 0.25) -> pd.DataFrame:
        """
        Runs the linear program to find the optimal charging/discharging schedule.
        
        :param market_data: DataFrame with 'timestamp', 'price_usd_per_mwh'. Optionally 'solar_generation_mw'.
        :param dt_hours: Time step duration in hours (default 0.25 for 15-min resolution).
        :return: DataFrame with the optimal schedule added.
        """
        # Create the linear solver with the GLOP backend.
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            raise Exception("Could not create solver GLOP")

        num_steps = len(market_data)
        
        # Decision Variables
        charge_vars = []
        discharge_vars = []
        soc_vars = []
        reserve_vars = []
        
        p_max = self.params['power_capacity_mw']
        e_max = self.params.get('max_soc_mwh', self.params['energy_capacity_mwh'])
        e_min = self.params.get('min_soc_mwh', 0.0)
        eff_c = self.params.get('charge_efficiency', 0.95)
        eff_d = self.params.get('discharge_efficiency', 0.95)
        
        # Initialize variables for all time steps
        for t in range(num_steps):
            charge_vars.append(solver.NumVar(0, p_max, f'charge_{t}'))
            discharge_vars.append(solver.NumVar(0, p_max, f'discharge_{t}'))
            soc_vars.append(solver.NumVar(e_min, e_max, f'soc_{t}'))
            reserve_vars.append(solver.NumVar(0, p_max, f'reserve_{t}'))

        # Constraints
        initial_soc = self.params.get('initial_soc_mwh', e_min)
        
        for t in range(num_steps):
            if t == 0:
                # First step depends on initial SOC
                solver.Add(soc_vars[t] == initial_soc + charge_vars[t] * dt_hours * eff_c - (discharge_vars[t] * dt_hours) / eff_d)
                
                # Feasibility constraint for reserve: if called upon, we must have enough SOC to deliver it
                solver.Add(initial_soc - (discharge_vars[t] + reserve_vars[t]) * dt_hours / eff_d >= e_min)
            else:
                # Subsequent steps depend on previous SOC
                solver.Add(soc_vars[t] == soc_vars[t-1] + charge_vars[t] * dt_hours * eff_c - (discharge_vars[t] * dt_hours) / eff_d)
                
                # Feasibility constraint for reserve
                solver.Add(soc_vars[t-1] - (discharge_vars[t] + reserve_vars[t]) * dt_hours / eff_d >= e_min)
                
            # Power limits for simultaneous discharge and reserve
            solver.Add(discharge_vars[t] + reserve_vars[t] <= p_max)
            
            # Since reserve and charging might physically conflict depending on inverter architecture,
            # we also add a constraint to prevent reserving beyond available inverter capacity while charging.
            solver.Add(charge_vars[t] + reserve_vars[t] <= p_max)

        # Objective Function: Maximize profit
        # Profit = Revenue from discharging + Revenue from reserve - Cost of charging
        objective = solver.Objective()
        for t in range(num_steps):
            price = market_data['price_usd_per_mwh'].iloc[t]
            ancillary_price = market_data.get('ancillary_price_usd_per_mw', pd.Series([0.0]*num_steps)).iloc[t]
            
            # Revenue from discharging
            objective.SetCoefficient(discharge_vars[t], price * dt_hours)
            # Revenue from reserving capacity (typically priced per MW/hour)
            objective.SetCoefficient(reserve_vars[t], ancillary_price * dt_hours)
            # Cost of charging (negative profit)
            objective.SetCoefficient(charge_vars[t], -price * dt_hours)
            
        objective.SetMaximization()

        # Solve the problem
        status = solver.Solve()

        # Extract results
        if status == pywraplp.Solver.OPTIMAL:
            results = market_data.copy()
            results['optimal_charge_mw'] = [v.solution_value() for v in charge_vars]
            results['optimal_discharge_mw'] = [v.solution_value() for v in discharge_vars]
            results['optimal_reserve_mw'] = [v.solution_value() for v in reserve_vars]
            results['optimal_soc_mwh'] = [v.solution_value() for v in soc_vars]
            
            # Calculate financials
            results['energy_revenue'] = results['optimal_discharge_mw'] * dt_hours * results['price_usd_per_mwh']
            
            if 'ancillary_price_usd_per_mw' in results.columns:
                results['ancillary_revenue'] = results['optimal_reserve_mw'] * dt_hours * results['ancillary_price_usd_per_mw']
            else:
                results['ancillary_revenue'] = 0.0
                
            results['cost'] = results['optimal_charge_mw'] * dt_hours * results['price_usd_per_mwh']
            results['profit'] = results['energy_revenue'] + results['ancillary_revenue'] - results['cost']
            
            return results
        else:
            raise Exception("The problem does not have an optimal solution.")

if __name__ == '__main__':
    # Quick test with synthetic data
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../data')))
    from synthetic_generator import generate_synthetic_data
    
    # Generate 3 days of data to test
    df_market = generate_synthetic_data(days=3)
    
    battery_params = {
        'power_capacity_mw': 5.0,
        'energy_capacity_mwh': 10.0,
        'charge_efficiency': 0.95,
        'discharge_efficiency': 0.95,
        'initial_soc_mwh': 5.0
    }
    
    optimizer = EnergyArbitrageOptimizer(battery_params)
    results = optimizer.optimize(df_market)
    
    print(f"Total Profit over 3 days: ${results['profit'].sum():.2f}")
    print(results[['timestamp', 'price_usd_per_mwh', 'optimal_charge_mw', 'optimal_discharge_mw', 'optimal_soc_mwh']].head(10))
