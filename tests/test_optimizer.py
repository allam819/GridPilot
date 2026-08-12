import unittest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from optimizer.optimizer import EnergyArbitrageOptimizer

class TestEnergyArbitrageOptimizer(unittest.TestCase):
    def setUp(self):
        self.battery_params = {
            'power_capacity_mw': 5.0,
            'energy_capacity_mwh': 10.0,
            'charge_efficiency': 1.0, # 100% for simple math in tests
            'discharge_efficiency': 1.0,
            'initial_soc_mwh': 0.0,
            'min_soc_mwh': 0.0,
            'max_soc_mwh': 10.0
        }
        self.optimizer = EnergyArbitrageOptimizer(self.battery_params)
        
        # Simple market data: 
        # t=0: price = 10 (cheap)
        # t=1: price = 100 (expensive)
        # t=2: price = 50 (medium)
        self.market_data = pd.DataFrame({
            'timestamp': pd.date_range('2025-01-01', periods=3, freq='15min'),
            'price_usd_per_mwh': [10.0, 100.0, 50.0]
        })

    def test_basic_arbitrage(self):
        # With 100% efficiency, it should charge when cheap and discharge when expensive.
        # Max power = 5.0 MW, so in 0.25 hrs, it can move 1.25 MWh.
        results = self.optimizer.optimize(self.market_data, dt_hours=0.25)
        
        # At t=0, price is 10, it should charge max power
        self.assertAlmostEqual(results.loc[0, 'optimal_charge_mw'], 5.0)
        self.assertAlmostEqual(results.loc[0, 'optimal_soc_mwh'], 1.25)
        
        # At t=1, price is 100, it should discharge what it has (1.25 MWh / 0.25h = 5.0 MW)
        self.assertAlmostEqual(results.loc[1, 'optimal_discharge_mw'], 5.0)
        self.assertAlmostEqual(results.loc[1, 'optimal_soc_mwh'], 0.0)

    def test_soc_limits(self):
        # If initial SOC is 10 (full), it can't charge more at t=0
        params = self.battery_params.copy()
        params['initial_soc_mwh'] = 10.0
        opt = EnergyArbitrageOptimizer(params)
        
        results = opt.optimize(self.market_data, dt_hours=0.25)
        # At t=0, it should not charge because it's full, but it might discharge since t=1 is better?
        # Actually, t=1 is $100. So it should hold at t=0 or discharge? 
        # t=0 price is 10, t=1 is 100, t=2 is 50.
        # It can discharge 5 MW at t=1 (1.25 MWh), and 5 MW at t=2 (1.25 MWh), etc.
        # Total energy 10 MWh, it can discharge 1.25 MWh at each step.
        # It should discharge at t=1 and t=2.
        self.assertAlmostEqual(results.loc[0, 'optimal_charge_mw'], 0.0)
        self.assertAlmostEqual(results.loc[1, 'optimal_discharge_mw'], 5.0)
        self.assertAlmostEqual(results.loc[2, 'optimal_discharge_mw'], 5.0)

if __name__ == '__main__':
    unittest.main()
