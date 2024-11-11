"""Internal module containing the `DC_IV` class for handling direct current IV data.

The class is designed to be used with the `Dataset` class from the `dataset` module to
parse, analyze, and visualize data from DC IV experiments.
"""  # noqa: N999

from collections.abc import Sequence

import pandas as pd


class DC_IV:  # noqa: N801
    def __init__(
        self,
        metadata: dict,
        dataframes: Sequence[pd.DataFrame],
        *,
        big_pad: bool = False,
    ) -> None:
        """Initialize the class instance with the given metadata and dataframes.

        Given metadata and dataframes are extracted using `Dataset._parse_datafile()`

        :param metadata: A dictionary containing metadata information.
        :param dataframes: A sequence of pandas DataFrames.
        """
        self.big_pad = big_pad
        self.data = dataframes[0]
        self.metadata = metadata
        self._init_metadata()

    def _init_metadata(self) -> None:
        """Help to initialize class members with metadata attributes."""
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
