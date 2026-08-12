import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_synthetic_data(start_date: str = '2025-01-01', days: int = 365, resolution_minutes: int = 15) -> pd.DataFrame:
    """
    Generates synthetic solar generation and electricity price data.
    
    Solar: Bell curve peaking at noon, zero at night, with daily weather noise.
    Prices: Duck curve profile with low/negative prices mid-day and evening spikes.
    """
    start_dt = pd.to_datetime(start_date)
    periods = int((days * 24 * 60) / resolution_minutes)
    
    # Generate timestamp index
    timestamps = [start_dt + timedelta(minutes=i*resolution_minutes) for i in range(periods)]
    df = pd.DataFrame({'timestamp': timestamps})
    
    # Pre-calculate hour and minute for easier profile generation
    df['hour'] = df['timestamp'].dt.hour
    df['minute'] = df['timestamp'].dt.minute
    df['time_float'] = df['hour'] + df['minute'] / 60.0
    
    # Generate daily weather noise (one scalar per day, repeating for all intervals in that day)
    # 0 = clear, 1 = cloudy. We use a simple random choice.
    daily_noise = np.random.uniform(0.8, 1.0, size=days) # 80% to 100% of clear sky
    # Introduce some very cloudy days (e.g., 20% drop)
    is_cloudy = np.random.choice([True, False], size=days, p=[0.2, 0.8])
    daily_noise[is_cloudy] *= 0.8
    
    # Map daily noise to each 15-min interval
    df['day_idx'] = (df.index * resolution_minutes) // (24 * 60)
    df['weather_factor'] = df['day_idx'].map(lambda d: daily_noise[d])
    
    # 1. Generate Solar Generation (Bell curve peaking at noon)
    # Normal distribution centered at 12:00, stdev of ~2.5 hours
    # Clip negative values (night time)
    peak_solar_mw = 5.0 # Max capacity
    df['solar_generation_mw'] = peak_solar_mw * np.exp(-0.5 * ((df['time_float'] - 12.0) / 2.5)**2)
    df['solar_generation_mw'] = df['solar_generation_mw'] * df['weather_factor']
    df.loc[(df['time_float'] < 6) | (df['time_float'] > 18.5), 'solar_generation_mw'] = 0.0
    
    # 2. Generate Electricity Prices (Duck Curve)
    # Base price
    base_price = 40.0 # $/MWh
    
    # Mid-day depression (11:00 - 14:00)
    mid_day_depression = -30.0 * np.exp(-0.5 * ((df['time_float'] - 12.5) / 1.5)**2)
    
    # Evening spike (18:00 - 21:00)
    evening_spike = 80.0 * np.exp(-0.5 * ((df['time_float'] - 19.5) / 1.5)**2)
    
    # Morning mini-spike
    morning_spike = 20.0 * np.exp(-0.5 * ((df['time_float'] - 8.0) / 1.0)**2)
    
    # Add randomization to prices (volatility)
    price_noise = np.random.normal(0, 5.0, size=periods)
    
    df['price_usd_per_mwh'] = base_price + mid_day_depression + evening_spike + morning_spike + price_noise
    
    # 3. Generate Ancillary Service Prices (e.g., Frequency Regulation or Spinning Reserve)
    # Base ancillary price is lower than energy, but can spike occasionally
    base_ancillary = 15.0 # $/MW
    ancillary_noise = np.random.normal(0, 2.0, size=periods)
    
    # Occasional high-value grid events (e.g., 5% chance of a spike)
    ancillary_spikes = np.random.choice([0.0, 50.0], size=periods, p=[0.95, 0.05])
    
    df['ancillary_price_usd_per_mw'] = base_ancillary + ancillary_noise + ancillary_spikes
    df['ancillary_price_usd_per_mw'] = df['ancillary_price_usd_per_mw'].clip(lower=0.0) # Reserve prices shouldn't be negative
    
    # Clean up temporary columns
    df = df.drop(columns=['hour', 'minute', 'time_float', 'day_idx', 'weather_factor'])
    
    return df

if __name__ == '__main__':
    df = generate_synthetic_data(days=365)
    print("Generated data shape:", df.shape)
    print(df.head(10))
    print("\nSummary Statistics:")
    print(df.describe())
    
    # Optionally save to CSV
    # df.to_csv('synthetic_market_data.csv', index=False)
