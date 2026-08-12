from celery import Celery
import os
import sys

# Add src to path to import gridpilot modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from db.repository import TimescaleRepository
from simulator.battery import Battery
from optimizer.optimizer import EnergyArbitrageOptimizer
from backtester.mpc_runner import MPCRunner
from optimizer.vpp_optimizer import VPPOptimizer
from backtester.vpp_mpc_runner import VPPMPCRunner

# Initialize Celery using dynamic Redis URL for Docker compatibility
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery(
    "gridpilot_worker",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Remove custom routing so tasks go to the default 'celery' queue
# celery_app.conf.task_routes = {
#     "app.worker.run_mpc_backtest_task": "main-queue",
#     "app.worker.run_digital_twin_task": "main-queue"
# }

@celery_app.task(bind=True)
def run_mpc_backtest_task(self, start_date: str, end_date: str, nodes_payload: list = None):
    """
    Asynchronous task to run the MPC backtest for a specific date range.
    """
    print(f"Starting MPC Backtest task for {start_date} to {end_date}")
    
    # In a fully integrated system, we would query `start_date` to `end_date` 
    # from TimescaleDB using TimescaleRepository.
    # For this scaffolding, we will simulate fetching the chunk.
    import asyncio
    
    # Normally: df_market = asyncio.run(repo.get_market_data_window(start_date, end_date))
    # Mocking data fetch for Celery scaffolding:
    import pandas as pd
    from datetime import datetime
    from data.synthetic_generator import generate_synthetic_data
    
    # Calculate days between dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    days = (end_dt - start_dt).days
    if days < 0:
        raise ValueError("End date must be after start date.")
    if days == 0:
        days = 1
        
    df_market = generate_synthetic_data(start_date=start_date, days=days)
    
    vpp_assets = nodes_payload if nodes_payload else [
        {
            'name': 'Default_Node',
            'power_capacity_mw': 5.0,
            'energy_capacity_mwh': 10.0,
            'charge_efficiency': 0.95,
            'discharge_efficiency': 0.95,
            'initial_soc_mwh': 0.0
        }
    ]
    
    # Ensure efficiencies are set if not provided in payload
    for asset in vpp_assets:
        if 'charge_efficiency' not in asset:
            asset['charge_efficiency'] = 0.95
        if 'discharge_efficiency' not in asset:
            asset['discharge_efficiency'] = 0.95
        if 'initial_soc_mwh' not in asset:
            asset['initial_soc_mwh'] = 0.0
    
    total_energy_rev = 0.0
    total_ancillary_rev = 0.0
    total_cost = 0.0
    total_energy_capacity = sum(b['energy_capacity_mwh'] for b in vpp_assets)
    total_power_capacity = sum(b['power_capacity_mw'] for b in vpp_assets)
    
    # 1. Initialize simultaneous VPP solver
    vpp_optimizer = VPPOptimizer(vpp_assets)
    batteries = [Battery(**b) for b in vpp_assets]
    vpp_mpc = VPPMPCRunner(vpp_optimizer, batteries, lookahead_hours=24.0, dt_hours=0.25)
    
    # 2. Run massive simultaneous loop
    all_results = vpp_mpc.run_mpc_loop(df_market)
    
    # 3. Calculate financials and Aggregate
    agg_results = all_results[0].copy()
    for a_idx, node_results in all_results.items():
        energy_rev = (node_results['discharge_mw'] * 0.25 * df_market['price_usd_per_mwh'].values).sum()
        cost = (node_results['charge_mw'] * 0.25 * df_market['price_usd_per_mwh'].values).sum()
        anc_prices = df_market.get('ancillary_price_usd_per_mw', df_market['price_usd_per_mwh'] * 0.3)
        ancillary_rev = (node_results['reserve_mw'] * 0.25 * anc_prices.values).sum()
        
        total_energy_rev += energy_rev
        total_cost += cost
        total_ancillary_rev += ancillary_rev
        
        if a_idx > 0:
            agg_results['charge_mw'] += node_results['charge_mw']
            agg_results['discharge_mw'] += node_results['discharge_mw']
            agg_results['reserve_mw'] += node_results['reserve_mw']
            agg_results['actual_soc_mwh'] += node_results['actual_soc_mwh']

    total_profit = (total_energy_rev + total_ancillary_rev) - total_cost
    
    immediate_row = agg_results.iloc[0]
    final_soc_pct = (immediate_row['actual_soc_mwh'] / total_energy_capacity) * 100
    
    if immediate_row['charge_mw'] > 0:
        action_text = f"CHARGE ({immediate_row['charge_mw']:.1f} MW)"
    elif immediate_row['discharge_mw'] > 0:
        action_text = f"DISCHARGE ({immediate_row['discharge_mw']:.1f} MW)"
    elif immediate_row['reserve_mw'] > 0:
        action_text = f"RESERVE ({immediate_row['reserve_mw']:.1f} MW)"
    else:
        action_text = "HOLD (0.0 MW)"
        
    explanation = all_results[0].iloc[0]['explanation']
    
    # Capture individual battery states for the UI
    individual_actions = []
    for a_idx, node_results in all_results.items():
        n_row = node_results.iloc[0]
        if n_row['charge_mw'] > 0:
            n_act = f"CHARGE ({n_row['charge_mw']:.1f} MW)"
        elif n_row['discharge_mw'] > 0:
            n_act = f"DISCHARGE ({n_row['discharge_mw']:.1f} MW)"
        elif n_row['reserve_mw'] > 0:
            n_act = f"RESERVE ({n_row['reserve_mw']:.1f} MW)"
        else:
            n_act = "HOLD (0.0 MW)"
            
        individual_actions.append({
            "name": vpp_assets[a_idx]['name'],
            "action": n_act,
            "soc": float((n_row['actual_soc_mwh'] / vpp_assets[a_idx]['energy_capacity_mwh']) * 100)
        })
        
    chart_data = []
    for idx, row in agg_results.iterrows():
        act_mw = float(row['charge_mw']) if row['charge_mw'] > 0 else float(-row['discharge_mw']) if row['discharge_mw'] > 0 else 0.0
        
        if row['charge_mw'] > 0:
            act = f"CHARGE ({row['charge_mw']:.1f} MW)"
        elif row['discharge_mw'] > 0:
            act = f"DISCHARGE ({row['discharge_mw']:.1f} MW)"
        elif row['reserve_mw'] > 0:
            act = f"RESERVE ({row['reserve_mw']:.1f} MW)"
        else:
            act = "HOLD (0.0 MW)"
            
        node1_exp = all_results[0].iloc[idx]['explanation']
        
        # Build base data
        data_point = {
            "time": row['timestamp'].strftime("%H:%M"),
            "price": float(df_market.loc[df_market['timestamp'] == row['timestamp'], 'price_usd_per_mwh'].values[0]),
            "solar": float(df_market.loc[df_market['timestamp'] == row['timestamp'], 'solar_generation_mw'].values[0]),
            "dispatch": act_mw, # Net total dispatch
            "soc": float((row['actual_soc_mwh'] / total_energy_capacity) * 100),
            "action": act,
            "explanation": str(node1_exp)
        }
        
        # Inject individual battery dispatches for stacked areas
        for a_idx, node_results in all_results.items():
            node_row = node_results.iloc[idx]
            n_act = float(node_row['charge_mw']) if node_row['charge_mw'] > 0 else float(-node_row['discharge_mw']) if node_row['discharge_mw'] > 0 else 0.0
            data_point[f"asset_{a_idx}"] = n_act
            
            # Individual SOC
            cap_mwh = vpp_assets[a_idx]['energy_capacity_mwh']
            n_soc = float((node_row['actual_soc_mwh'] / cap_mwh) * 100) if cap_mwh > 0 else 0.0
            data_point[f"soc_asset_{a_idx}"] = n_soc
            
        chart_data.append(data_point)

    return {
        "status": "SUCCESS",
        "start_date": start_date,
        "end_date": end_date,
        "metrics": {
            "Total Power Capacity (MW)": float(total_power_capacity),
            "Total Energy Capacity (MWh)": float(total_energy_capacity),
            "Total Profit ($)": float(total_profit),
            "Energy Revenue ($)": float(total_energy_rev),
            "Ancillary Revenue ($)": float(total_ancillary_rev),
            "Cost ($)": float(total_cost),
            "Steps Processed": len(agg_results),
            "Final SOC (%)": float(final_soc_pct),
            "Current Action": action_text,
            "Explanation": str(explanation),
            "individual_actions": individual_actions,
            "chart_data": chart_data
        }
    }

@celery_app.task(bind=True)
def run_digital_twin_task(self, baseline_params: dict, target_params: dict, capex_per_mwh: float):
    """
    Asynchronous task to run the comparative digital twin simulations.
    """
    print("Starting Digital Twin task...")
    
    # Mocking data fetch
    from data.synthetic_generator import generate_synthetic_data
    df_market = generate_synthetic_data(days=30)
    
    from simulator.digital_twin import DigitalTwinRunner
    runner = DigitalTwinRunner(df_market, lookahead_hours=24.0, dt_hours=0.25)
    
    # Run Baseline
    print("Simulation 0/2: Running baseline...")
    # (runner.run_comparative_simulation runs both, but we can do it step-by-step or just let it log inside).
    # Since we want to log specifically 'Simulation 1/2 complete', we'll let the runner do it or wrap it.
    
    # Actually, we already built run_comparative_simulation in the runner. Let's just call it.
    print("Simulation 1/2 in progress (Baseline)...")
    results = runner.run_comparative_simulation(baseline_params, target_params, capex_per_mwh)
    print("Simulation 2/2 complete (Target).")
    
    return {
        "status": "SUCCESS",
        "results": results
    }
