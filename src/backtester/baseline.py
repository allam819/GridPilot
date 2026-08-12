import pandas as pd

class RuleBasedBaseline:
    def __init__(self, battery_simulator, charge_start_hour=11, charge_end_hour=14, discharge_start_hour=18, discharge_end_hour=21):
        self.battery = battery_simulator
        self.charge_start = charge_start_hour
        self.charge_end = charge_end_hour
        self.discharge_start = discharge_start_hour
        self.discharge_end = discharge_end_hour
        
    def run(self, market_data: pd.DataFrame, dt_hours: float = 0.25):
        """
        Run a simple rule-based schedule to benchmark against MPC.
        Rule: Charge mid-day (duck curve low), discharge evening (duck curve peak).
        No reserve.
        """
        print("Running Rule-Based Baseline...")
        executed_actions = []
        
        for idx, row in market_data.iterrows():
            hour = row['timestamp'].hour
            
            command_charge = 0.0
            command_discharge = 0.0
            
            if self.charge_start <= hour < self.charge_end:
                # Charge at maximum power if we are in the charging window
                command_charge = self.battery.power_capacity
            elif self.discharge_start <= hour < self.discharge_end:
                # Discharge at maximum power if we are in the discharging window
                command_discharge = self.battery.power_capacity
                
            # Step the battery to get actual SOC and apply limits physically
            actual_soc = self.battery.step(
                charge_power_mw=command_charge,
                discharge_power_mw=command_discharge,
                duration_hours=dt_hours
            )
            
            # Since the battery simulator enforces max capacity, the actual charge/discharge 
            # might be less than the command. We record the commands here for simplicity.
            # Real energy transaction = delta SOC.
            
            executed_actions.append({
                'timestamp': row['timestamp'],
                'charge_mw': command_charge,
                'discharge_mw': command_discharge,
                'reserve_mw': 0.0,
                'actual_soc_mwh': actual_soc
            })
            
        return pd.DataFrame(executed_actions)
