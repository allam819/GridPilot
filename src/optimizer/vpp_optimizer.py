import pandas as pd
from ortools.linear_solver import pywraplp

class VPPOptimizer:
    def __init__(self, assets: list[dict]):
        """
        :param assets: list of dictionaries containing battery specs.
        """
        self.assets = assets

    def optimize(self, market_data: pd.DataFrame, dt_hours: float = 0.25) -> dict:
        """
        Runs a 2D linear program to find the optimal schedule for ALL assets simultaneously,
        subject to physical asset constraints and a global grid connection limit.
        """
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            raise Exception("Could not create solver GLOP")

        num_steps = len(market_data)
        num_assets = len(self.assets)
        
        # Global Grid Limit (e.g., 80% of total max power to force synergistic behavior)
        total_p_max = sum(a['power_capacity_mw'] for a in self.assets)
        grid_limit = total_p_max * 0.8
        
        # 2D Matrices for Decision Variables
        charge_vars = [[None]*num_steps for _ in range(num_assets)]
        discharge_vars = [[None]*num_steps for _ in range(num_assets)]
        soc_vars = [[None]*num_steps for _ in range(num_assets)]
        reserve_vars = [[None]*num_steps for _ in range(num_assets)]
        
        for a_idx, asset in enumerate(self.assets):
            p_max = asset['power_capacity_mw']
            e_max = asset.get('max_soc_mwh', asset['energy_capacity_mwh'])
            e_min = asset.get('min_soc_mwh', 0.0)
            
            for t in range(num_steps):
                charge_vars[a_idx][t] = solver.NumVar(0, p_max, f'charge_{a_idx}_{t}')
                discharge_vars[a_idx][t] = solver.NumVar(0, p_max, f'discharge_{a_idx}_{t}')
                soc_vars[a_idx][t] = solver.NumVar(e_min, e_max, f'soc_{a_idx}_{t}')
                reserve_vars[a_idx][t] = solver.NumVar(0, p_max, f'reserve_{a_idx}_{t}')

        # Constraints
        for a_idx, asset in enumerate(self.assets):
            p_max = asset['power_capacity_mw']
            e_min = asset.get('min_soc_mwh', 0.0)
            eff_c = asset.get('charge_efficiency', 0.95)
            eff_d = asset.get('discharge_efficiency', 0.95)
            initial_soc = asset.get('initial_soc_mwh', e_min)
            
            for t in range(num_steps):
                if t == 0:
                    solver.Add(soc_vars[a_idx][t] == initial_soc + charge_vars[a_idx][t] * dt_hours * eff_c - (discharge_vars[a_idx][t] * dt_hours) / eff_d)
                    solver.Add(initial_soc - (discharge_vars[a_idx][t] + reserve_vars[a_idx][t]) * dt_hours / eff_d >= e_min)
                else:
                    solver.Add(soc_vars[a_idx][t] == soc_vars[a_idx][t-1] + charge_vars[a_idx][t] * dt_hours * eff_c - (discharge_vars[a_idx][t] * dt_hours) / eff_d)
                    solver.Add(soc_vars[a_idx][t-1] - (discharge_vars[a_idx][t] + reserve_vars[a_idx][t]) * dt_hours / eff_d >= e_min)
                    
                solver.Add(discharge_vars[a_idx][t] + reserve_vars[a_idx][t] <= p_max)
                solver.Add(charge_vars[a_idx][t] + reserve_vars[a_idx][t] <= p_max)
                
        # Global Portfolio Constraints (Site grid connection limit)
        for t in range(num_steps):
            solver.Add(sum(discharge_vars[a_idx][t] for a_idx in range(num_assets)) <= grid_limit)

        # Objective Function
        objective = solver.Objective()
        for t in range(num_steps):
            price = market_data['price_usd_per_mwh'].iloc[t]
            ancillary_price = market_data.get('ancillary_price_usd_per_mw', pd.Series([0.0]*num_steps)).iloc[t]
            
            for a_idx in range(num_assets):
                objective.SetCoefficient(discharge_vars[a_idx][t], price * dt_hours)
                objective.SetCoefficient(reserve_vars[a_idx][t], ancillary_price * dt_hours)
                objective.SetCoefficient(charge_vars[a_idx][t], -price * dt_hours)
                
        objective.SetMaximization()
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL:
            results = {}
            for a_idx in range(num_assets):
                df = market_data.copy()
                df['optimal_charge_mw'] = [v.solution_value() for v in charge_vars[a_idx]]
                df['optimal_discharge_mw'] = [v.solution_value() for v in discharge_vars[a_idx]]
                df['optimal_reserve_mw'] = [v.solution_value() for v in reserve_vars[a_idx]]
                df['optimal_soc_mwh'] = [v.solution_value() for v in soc_vars[a_idx]]
                results[a_idx] = df
            return results
        else:
            raise Exception("No optimal solution found for VPP Matrix.")
