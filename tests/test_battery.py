import unittest
import sys
import os

# Add src directory to path to import simulator
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from simulator.battery import Battery

class TestBatterySimulator(unittest.TestCase):
    def setUp(self):
        # 10 MWh, 5 MW battery, initially at 50% SOC
        self.battery = Battery(
            name="TestBESS", 
            energy_capacity_mwh=10.0, 
            power_capacity_mw=5.0,
            initial_soc_mwh=5.0,
            charge_efficiency=0.9,
            discharge_efficiency=0.9
        )

    def test_initial_state(self):
        self.assertEqual(self.battery.current_soc, 5.0)
        self.assertEqual(self.battery.get_soc_percentage(), 50.0)

    def test_charging(self):
        # Charge at 5 MW for 1 hour
        soc = self.battery.step(charge_power_mw=5.0, discharge_power_mw=0.0, duration_hours=1.0)
        # Expected SOC = 5.0 + (5.0 * 1.0 * 0.9) = 5.0 + 4.5 = 9.5
        self.assertEqual(soc, 9.5)
        
    def test_discharging(self):
        # Discharge at 4.5 MW for 1 hour
        # Required energy from battery = 4.5 * 1.0 / 0.9 = 5.0
        soc = self.battery.step(charge_power_mw=0.0, discharge_power_mw=4.5, duration_hours=1.0)
        # Expected SOC = 5.0 - 5.0 = 0.0
        self.assertEqual(soc, 0.0)

    def test_power_limits(self):
        # Try to charge at 10 MW, but max is 5 MW. Duration 1 hour.
        # So actual charge should be 5 MW * 1 hr * 0.9 = 4.5 MWh
        soc = self.battery.step(charge_power_mw=10.0, discharge_power_mw=0.0, duration_hours=1.0)
        self.assertEqual(soc, 9.5)

    def test_energy_limits_max(self):
        # Charge at 5 MW for 2 hours -> 5 * 2 * 0.9 = 9 MWh
        # 5.0 + 9.0 = 14.0, which exceeds 10.0 max capacity.
        soc = self.battery.step(charge_power_mw=5.0, discharge_power_mw=0.0, duration_hours=2.0)
        self.assertEqual(soc, 10.0)

    def test_energy_limits_min(self):
        # Discharge at 5 MW for 2 hours -> 5 * 2 / 0.9 = 11.11 MWh required
        # 5.0 - 11.11 < 0, should bottom out at 0
        soc = self.battery.step(charge_power_mw=0.0, discharge_power_mw=5.0, duration_hours=2.0)
        self.assertEqual(soc, 0.0)

if __name__ == '__main__':
    unittest.main()
