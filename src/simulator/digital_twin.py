from simulator.battery import Battery
from optimizer.optimizer import EnergyArbitrageOptimizer
from backtester.mpc_runner import MPCRunner

class DigitalTwinRunner:
    def __init__(self, df_market, dt_hours: float = 0.25, lookahead_hours: float = 24.0):
        self.df_market = df_market
        self.dt_hours = dt_hours
        self.lookahead_hours = lookahead_hours
        
    def run_comparative_simulation(self, baseline_params: dict, target_params: dict, capex_per_mwh: float):
        """
        Runs dual MPC backtests for the baseline and target battery configurations over the same market data.
        Returns the financial metrics for both, and a comparative analysis (Incremental profit, Payback period).
        """
        # --- Baseline Simulation ---
        print("Starting Digital Twin: Baseline Simulation")
        baseline_battery = Battery(**baseline_params)
        baseline_optimizer = EnergyArbitrageOptimizer(baseline_params)
        baseline_mpc = MPCRunner(baseline_optimizer, baseline_battery, self.lookahead_hours, self.dt_hours)
        baseline_results = baseline_mpc.run_mpc_loop(self.df_market)
        
        # Calculate baseline profit
        b_energy_rev = (baseline_results['discharge_mw'] * self.dt_hours * self.df_market['price_usd_per_mwh'].values).sum()
        b_ancillary_rev = (baseline_results['reserve_mw'] * self.dt_hours * self.df_market['ancillary_price_usd_per_mw'].values).sum()
        b_cost = (baseline_results['charge_mw'] * self.dt_hours * self.df_market['price_usd_per_mwh'].values).sum()
        baseline_profit = b_energy_rev + b_ancillary_rev - b_cost
        
        # --- Target Simulation ---
        print("Starting Digital Twin: Target Simulation")
        target_battery = Battery(**target_params)
        target_optimizer = EnergyArbitrageOptimizer(target_params)
        target_mpc = MPCRunner(target_optimizer, target_battery, self.lookahead_hours, self.dt_hours)
        target_results = target_mpc.run_mpc_loop(self.df_market)
        
        # Calculate target profit
        t_energy_rev = (target_results['discharge_mw'] * self.dt_hours * self.df_market['price_usd_per_mwh'].values).sum()
        t_ancillary_rev = (target_results['reserve_mw'] * self.dt_hours * self.df_market['ancillary_price_usd_per_mw'].values).sum()
        t_cost = (target_results['charge_mw'] * self.dt_hours * self.df_market['price_usd_per_mwh'].values).sum()
        target_profit = t_energy_rev + t_ancillary_rev - t_cost
        
        # --- Comparative Analysis ---
        incremental_profit = target_profit - baseline_profit
        
        # Calculate CapEx (cost of hardware upgrade)
        added_capacity = target_params['energy_capacity_mwh'] - baseline_params['energy_capacity_mwh']
        total_capex = max(0, added_capacity * capex_per_mwh)
        
        # Annualize profit if simulation is less than 365 days (extrapolate simply)
        days_simulated = len(self.df_market) * self.dt_hours / 24
        annual_multiplier = 365.0 / days_simulated if days_simulated > 0 else 0
        annualized_incremental_profit = incremental_profit * annual_multiplier
        
        payback_years = (total_capex / annualized_incremental_profit) if annualized_incremental_profit > 0 else float('inf')
        
        return {
            "baseline_config": {
                "name": baseline_params.get("name", "Baseline"),
                "power_capacity_mw": baseline_params["power_capacity_mw"],
                "energy_capacity_mwh": baseline_params["energy_capacity_mwh"],
                "profit": float(baseline_profit),
                "energy_revenue": float(b_energy_rev),
                "ancillary_revenue": float(b_ancillary_rev),
                "cost": float(b_cost)
            },
            "target_config": {
                "name": target_params.get("name", "Target"),
                "power_capacity_mw": target_params["power_capacity_mw"],
                "energy_capacity_mwh": target_params["energy_capacity_mwh"],
                "profit": float(target_profit),
                "energy_revenue": float(t_energy_rev),
                "ancillary_revenue": float(t_ancillary_rev),
                "cost": float(t_cost)
            },
            "comparative_analysis": {
                "incremental_simulated_profit": float(incremental_profit),
                "annualized_incremental_profit": float(annualized_incremental_profit),
                "added_capacity_mwh": float(added_capacity),
                "capex_per_mwh": float(capex_per_mwh),
                "total_capex": float(total_capex),
                "payback_period_years": float(payback_years)
            }
        }
