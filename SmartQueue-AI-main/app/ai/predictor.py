import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

class WaitTimePredictor:
    def __init__(self):
        self.model = LinearRegression()
        self.trained = False

    def train_initial_model(self, data: pd.DataFrame = None):
        if data is None or len(data) < 20:
            self.trained = False
            return

        X = data[["queue_length", "active_staff", "hour", "day"]]
        y = data["wait_time"]

        self.model.fit(X, y)
        self.trained = True

    def predict(self, queue_length, active_staff, hour, day):
        if not self.trained or active_staff == 0:
            return queue_length * 5  # fallback

        prediction = self.model.predict(
            [[queue_length, active_staff, hour, day]]
        )[0]

        return max(1, int(prediction))
