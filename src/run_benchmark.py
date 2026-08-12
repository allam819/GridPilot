import asyncio
import pandas as pd
from data.synthetic_generator import generate_synthetic_data
from db.models import init_db
from db.repository import TimescaleRepository
from simulator.battery import Battery
from optimizer.optimizer import EnergyArbitrageOptimizer
from backtester.mpc_runner import MPCRunner
from backtester.baseline import RuleBasedBaseline
import time

async def main():
    print("--- 1. Initializing Database ---")
    await init_db()
    
    print("\n--- 2. Generating Synthetic Data ---")
    # Generate 30 days of data for the benchmark
    df_market = generate_synthetic_data(days=30)
    
    print("\n--- 3. Bulk Inserting to TimescaleDB ---")
    repo = TimescaleRepository()
    await repo.bulk_insert_market_data(df_market)
    
    # 4. Setup common battery parameters
    battery_params = {
        'name': 'BenchmarkBESS',
        'power_capacity_mw': 5.0,
        'energy_capacity_mwh': 10.0,
        'charge_efficiency': 0.95,
        'discharge_efficiency': 0.95,
        'initial_soc_mwh': 0.0,
        'min_soc_mwh': 0.0,
        'max_soc_mwh': 10.0
    }
    
    print("\n--- 4. Running Rule-Based Baseline ---")
    # Re-instantiate a fresh battery for the baseline
    baseline_battery = Battery(**battery_params)
    baseline = RuleBasedBaseline(baseline_battery)
    
    start_time = time.time()
    baseline_results = baseline.run(df_market, dt_hours=0.25)
    baseline_duration = time.time() - start_time
    
    # Calculate baseline revenue metrics (baseline has no reserve revenue)
    # The actual revenue comes from delta SOC * price, but our baseline records charge/discharge commands.
    # To be precise, energy revenue = discharge * dt * price, cost = charge * dt * price
    baseline_results['price_usd_per_mwh'] = df_market['price_usd_per_mwh'].values
    # Note: baseline commands might be higher than actual due to limits, but we'll approximate 
    # based on actual SOC changes if needed, or just use the commands assuming the battery absorbed them.
    # We'll use the commands for a rough estimate, or properly calculate based on physical constraints.
    # The physical simulator enforces bounds, so actual power might be lower. 
    # For a fair comparison, let's calculate actual power from delta SOC.
    
    actual_power_list = []
    prev_soc = battery_params['initial_soc_mwh']
    for idx, row in baseline_results.iterrows():
        current_soc = row['actual_soc_mwh']
        delta_soc = current_soc - prev_soc
        # If delta_soc > 0, it was charging. charge_power = delta_soc / (dt * eff_c)
        if delta_soc > 0:
            actual_charge = delta_soc / (0.25 * battery_params['charge_efficiency'])
            actual_discharge = 0.0
        else:
            # discharging. discharge_power = -delta_soc * eff_d / dt
            actual_charge = 0.0
            actual_discharge = (-delta_soc * battery_params['discharge_efficiency']) / 0.25
        actual_power_list.append((actual_charge, actual_discharge))
        prev_soc = current_soc
        
    actual_charge_arr = pd.Series([x[0] for x in actual_power_list])
    actual_discharge_arr = pd.Series([x[1] for x in actual_power_list])
    
    base_revenue = (actual_discharge_arr * 0.25 * df_market['price_usd_per_mwh']).sum()
    base_cost = (actual_charge_arr * 0.25 * df_market['price_usd_per_mwh']).sum()
    base_profit = base_revenue - base_cost

    print("\n--- 5. Running GridPilot MPC Backtester ---")
    # Fresh battery for MPC
    mpc_battery = Battery(**battery_params)
    optimizer = EnergyArbitrageOptimizer(battery_params)
    
    mpc = MPCRunner(optimizer, mpc_battery, lookahead_hours=24.0, dt_hours=0.25)
    
    start_time = time.time()
    mpc_results = mpc.run_mpc_loop(df_market)
    mpc_duration = time.time() - start_time
    
    # Calculate MPC metrics
    mpc_results['price_usd_per_mwh'] = df_market['price_usd_per_mwh'].values
    mpc_results['ancillary_price_usd_per_mw'] = df_market['ancillary_price_usd_per_mw'].values
    
    mpc_energy_rev = (mpc_results['discharge_mw'] * 0.25 * mpc_results['price_usd_per_mwh']).sum()
    mpc_cost = (mpc_results['charge_mw'] * 0.25 * mpc_results['price_usd_per_mwh']).sum()
    mpc_ancillary_rev = (mpc_results['reserve_mw'] * 0.25 * mpc_results['ancillary_price_usd_per_mw']).sum()
    mpc_profit = mpc_energy_rev + mpc_ancillary_rev - mpc_cost
    
    print("\n==================================================")
    print("          BENCHMARK COMPARISON (30 DAYS)          ")
    print("==================================================")
    
    print("\n[ Rule-Based Baseline ]")
    print(f"Energy Revenue:    ${base_revenue:,.2f}")
    print(f"Energy Cost:       ${base_cost:,.2f}")
    print(f"Ancillary Revenue: $0.00")
    print(f"Net Profit:        ${base_profit:,.2f}")
    print(f"Execution Time:    {baseline_duration:.2f} seconds")
    
    print("\n[ GridPilot MPC ]")
    print(f"Energy Revenue:    ${mpc_energy_rev:,.2f}")
    print(f"Energy Cost:       ${mpc_cost:,.2f}")
    print(f"Ancillary Revenue: ${mpc_ancillary_rev:,.2f}")
    print(f"Net Profit:        ${mpc_profit:,.2f}")
    print(f"Execution Time:    {mpc_duration:.2f} seconds")
    
    print("\n==================================================")
    print(f"IMPROVEMENT vs BASELINE: +${(mpc_profit - base_profit):,.2f}")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
