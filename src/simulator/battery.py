class Battery:
    def __init__(self, name: str, energy_capacity_mwh: float, power_capacity_mw: float, 
                 initial_soc_mwh: float = 0.0, min_soc_mwh: float = 0.0, max_soc_mwh: float = None,
                 charge_efficiency: float = 0.95, discharge_efficiency: float = 0.95):
        """
        Initialize the Battery simulator.
        
        :param name: Identifier for the battery.
        :param energy_capacity_mwh: Total energy capacity in MWh.
        :param power_capacity_mw: Maximum power for charging/discharging in MW.
        :param initial_soc_mwh: Starting State of Charge in MWh.
        :param min_soc_mwh: Minimum allowed SOC in MWh.
        :param max_soc_mwh: Maximum allowed SOC in MWh (defaults to energy_capacity_mwh).
        :param charge_efficiency: Efficiency of charging (0 to 1).
        :param discharge_efficiency: Efficiency of discharging (0 to 1).
        """
        self.name = name
        self.energy_capacity = energy_capacity_mwh
        self.power_capacity = power_capacity_mw
        
        self.min_soc = min_soc_mwh
        self.max_soc = max_soc_mwh if max_soc_mwh is not None else energy_capacity_mwh
        
        # Current state
        self.current_soc = min(max(initial_soc_mwh, self.min_soc), self.max_soc)
        
        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency

    def step(self, charge_power_mw: float, discharge_power_mw: float, duration_hours: float) -> float:
        """
        Advance the battery state by a given time step based on charge and discharge commands.
        
        :param charge_power_mw: Commanded charge power in MW.
        :param discharge_power_mw: Commanded discharge power in MW.
        :param duration_hours: Duration of the time step in hours.
        :return: The new State of Charge (SOC) in MWh.
        """
        # Ensure power commands don't exceed physical limits
        actual_charge_power = min(max(charge_power_mw, 0), self.power_capacity)
        actual_discharge_power = min(max(discharge_power_mw, 0), self.power_capacity)
        
        # Calculate energy changes
        # Energy added to the battery is charge_power * time * efficiency
        energy_added = actual_charge_power * duration_hours * self.charge_efficiency
        
        # Energy removed from the battery is discharge_power * time / efficiency
        energy_removed = (actual_discharge_power * duration_hours) / self.discharge_efficiency
        
        # Update SOC
        new_soc = self.current_soc + energy_added - energy_removed
        
        # Enforce SOC bounds
        self.current_soc = min(max(new_soc, self.min_soc), self.max_soc)
        
        return self.current_soc

    def get_soc_percentage(self) -> float:
        """Return the current SOC as a percentage (0 to 100)."""
        if self.energy_capacity == 0:
            return 0.0
        return (self.current_soc / self.energy_capacity) * 100.0

    def __repr__(self):
        return f"<Battery '{self.name}' SOC: {self.current_soc:.2f}/{self.energy_capacity:.2f} MWh ({self.get_soc_percentage():.1f}%)>"
