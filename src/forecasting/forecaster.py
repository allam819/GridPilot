import pandas as pd
import numpy as np
import xgboost as xgb

class ForecastingEngine:
    def __init__(self):
        self.price_model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, objective='reg:squarederror')
        self.solar_model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=5, objective='reg:squarederror')
        
    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates chronological and lagged features for the XGBoost model.
        Assumes df has 'timestamp', 'price_usd_per_mwh', 'solar_generation_mw'.
        """
        df_feat = df.copy()
        
        # Time-based features
        df_feat['hour_of_day'] = df_feat['timestamp'].dt.hour
        df_feat['day_of_week'] = df_feat['timestamp'].dt.dayofweek
        df_feat['day_of_year'] = df_feat['timestamp'].dt.dayofyear
        
        # We assume 15-minute resolution, so:
        # 24 hours = 96 steps
        # 48 hours = 192 steps
        # 168 hours (7 days) = 672 steps
        
        df_feat['price_lag_24h'] = df_feat['price_usd_per_mwh'].shift(96)
        df_feat['price_lag_48h'] = df_feat['price_usd_per_mwh'].shift(192)
        df_feat['price_lag_168h'] = df_feat['price_usd_per_mwh'].shift(672)
        
        df_feat['solar_lag_24h'] = df_feat['solar_generation_mw'].shift(96)
        df_feat['solar_lag_48h'] = df_feat['solar_generation_mw'].shift(192)
        
        # Drop rows with NaN values resulting from the lag shift
        df_feat = df_feat.dropna()
        
        return df_feat

    def train(self, df_train: pd.DataFrame):
        """
        Train the forecasting models on the chronological training split.
        """
        df_feat = self._create_features(df_train)
        
        # Features for price prediction
        X_price = df_feat[['hour_of_day', 'day_of_week', 'day_of_year', 'price_lag_24h', 'price_lag_48h', 'price_lag_168h']]
        y_price = df_feat['price_usd_per_mwh']
        self.price_model.fit(X_price, y_price)
        
        # Features for solar prediction
        X_solar = df_feat[['hour_of_day', 'day_of_week', 'day_of_year', 'solar_lag_24h', 'solar_lag_48h']]
        y_solar = df_feat['solar_generation_mw']
        self.solar_model.fit(X_solar, y_solar)
        
        print("ForecastingEngine: Models trained successfully.")

    def forecast(self, df_lookahead_context: pd.DataFrame) -> pd.DataFrame:
        """
        Generate forecasts for a given lookahead window.
        df_lookahead_context must contain the past 168 hours of data so features can be built.
        """
        df_feat = self._create_features(df_lookahead_context)
        
        X_price = df_feat[['hour_of_day', 'day_of_week', 'day_of_year', 'price_lag_24h', 'price_lag_48h', 'price_lag_168h']]
        X_solar = df_feat[['hour_of_day', 'day_of_week', 'day_of_year', 'solar_lag_24h', 'solar_lag_48h']]
        
        forecast_df = pd.DataFrame({'timestamp': df_feat['timestamp']})
        forecast_df['predicted_price_usd_per_mwh'] = self.price_model.predict(X_price)
        forecast_df['predicted_solar_generation_mw'] = self.solar_model.predict(X_solar)
        
        # Clip solar to prevent negative generation
        forecast_df['predicted_solar_generation_mw'] = forecast_df['predicted_solar_generation_mw'].clip(lower=0.0)
        
        return forecast_df
