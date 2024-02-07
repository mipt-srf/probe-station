from collections.abc import Sequence

import pandas as pd


class DC_IV:
    def __init__(self, metadata: dict, dataframes: Sequence[pd.DataFrame]) -> None:
        self.data = dataframes[0]
        self.metadata = metadata
        self._init_metadata()

    def _init_metadata(self):
        self.measurement = self.metadata["Measurement Number"]
        self.measurement_id = self.metadata["Measurement ID"]
        self.series_id = self.metadata["SeriesID"]
        self.mode = self.metadata["MeasureMode"]
        self.first_bias = self.metadata["Bias1"]
        self.second_bias = self.metadata["Bias2"]
        self.step = self.metadata["Step"]
        self.pos_compliance = self.metadata["Positive compliance"]
        self.neg_compliance = self.metadata["Negative compliance"]
        self.steps = self.metadata["RealMeasuredPoints"]
