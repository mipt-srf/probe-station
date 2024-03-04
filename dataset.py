import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from probe_station._CV import CV
from probe_station._DC_IV import DC_IV
from probe_station._PQ_PUND import PQ_PUND


def is_float(string: str):
    """Returns True if string is convertible to float, False otherwise"""
    try:
        float(string)
        return True
    except (ValueError, TypeError):  # str and None
        return False


def yield_pairs(lst: Sequence):
    """Yield pairs of elems from iterable and subscriptable object"""
    for pair in zip(lst[::2], lst[1::2]):
        yield pair


def non_numeric_row(df: pd.DataFrame):
    """Find index of first row with non-numerical values"""
    return np.argmin(df.map(is_float).all(axis=1))


class Dataset:
    def __init__(self, path: Path, big_pad: bool = False):
        plt.rcParams.update({"font.size": 13})
        self.path = path
        metadata, dataframes = self._parse_datafile()
        self.metadata = metadata
        self.dataframes = dataframes

        handlers = {"PQPUND": PQ_PUND, "DC IV": DC_IV, "CVS": CV}
        mode = metadata["Measurement type"]
        self.handler = handlers[mode](metadata, dataframes, big_pad)

    def _parse_datafile(self):
        with open(self.path, "r") as file:
            metadata = self._parse_metadata(file)
            lines = file.readlines()
        mode = metadata["Measurement type"]
        additive = 1 if mode == "PQPUND" else 0
        if mode == "PQPUND":
            columns = 3
        if mode == "CVS":
            columns = 5
        if mode == "DC IV":
            columns = 3
        data = [
            line.strip().split()
            for line in lines[len(metadata.keys()) + 1 + additive :]
        ]

        df = pd.DataFrame(data[1:]).iloc[:, :columns].dropna(how="all")
        df.columns = data[0]  # type: ignore
        dataframes = []
        while True:
            row = non_numeric_row(df)
            if row == 0:
                dataframes.append(df.map(float).reset_index(drop=True))
                break
            numeric_df = df.iloc[:row].map(float).reset_index(drop=True)
            dataframes.append(numeric_df)
            df = df.iloc[row + 2 :].dropna(axis=1, how="all")
        row = non_numeric_row(df)
        return metadata, dataframes

    def _parse_metadata(self, file):
        lines = [line for line in file if not line.isspace()]  # drop empty lines
        metadata = {}
        for header_str, value_str in yield_pairs(lines):
            headers_pattern = r"\s*([A-Z][a-z]+\d?(?: ?[a-zA-Z]+)*)"
            headers = re.findall(headers_pattern, header_str)

            values_pattern = r"-?(?:\d+\.\d+|\de-\d\d|\d+|[A-Z]+ ?[A-Z]+)"
            values = re.findall(values_pattern, value_str)

            for i, value in enumerate(values):
                if value.isnumeric():
                    values[i] = int(value)
                elif is_float(value):
                    values[i] = float(value)

            metadata.update({key: value for key, value in zip(headers, values)})
            file.seek(0)  # return cursor to the beginning

        return metadata
