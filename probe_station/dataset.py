"""Module for reading probe station data files.

It also provides an interface to the various processing functions that
are most typical to a particular measurement mode.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from probe_station._CV import CV
from probe_station._DC_IV import DC_IV
from probe_station._PQ_PUND import PQ_PUND

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence


def is_float(string: str) -> bool:
    """Return ``True`` if string is convertible to `float`, ``False`` otherwise."""
    try:
        float(string)
    except (ValueError, TypeError):  # str and None
        return False
    else:
        return True


def yield_pairs(lst: Sequence) -> Generator[tuple[Any, Any], None, None]:
    """Yield pairs of elems from iterable and subscriptable object."""
    yield from zip(lst[::2], lst[1::2], strict=False)


def non_numeric_row(df: pd.DataFrame) -> np.intp:
    """Find index of first row with non-numerical values."""
    return np.argmin(df.map(is_float).all(axis=1))


class Dataset:
    """Class for reading probe station data files."""

    def __init__(self, path: Path, *, big_pad: bool = False) -> None:
        """Initialize the class instance with the given datafile path.

        Chooses the appropriate handler for data processing based on the
        measurement mode.

        :param path: Path to the datafile.
        :param big_pad: ``True`` if the pad is 100um^2, ``False`` if 25um^2.
        """
        plt.rcParams.update({"font.size": 13})
        self.path = path
        metadata, dataframes = self._parse_datafile()
        self.metadata = metadata
        self.dataframes = dataframes

        handlers = {"PQPUND": PQ_PUND, "DC IV": DC_IV, "CVS": CV}
        mode = metadata["Measurement type"]
        self.handler = handlers[mode](metadata, dataframes, big_pad=big_pad)

    def _parse_datafile(self) -> tuple[dict[str, Any], list[pd.DataFrame]]:
        """Parse the datafile and returns metadata and dataframes.

        :return: Metadata and dataframes.
        """
        with Path.open(self.path) as file:
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
        data_list = [
            line.strip().split()
            for line in lines[len(metadata.keys()) + 1 + additive :]
        ]

        data = pd.DataFrame(data_list[1:]).iloc[:, :columns].dropna(how="all")
        data.columns = data_list[0]  # type: ignore
        dataframes = []
        while True:
            row = non_numeric_row(data)
            if row == 0:
                dataframes.append(data.map(float).reset_index(drop=True))
                break
            numeric_df = data.iloc[:row].map(float).reset_index(drop=True)
            dataframes.append(numeric_df)
            data = data.iloc[row + 2 :].dropna(axis=1, how="all")
        row = non_numeric_row(data)
        return metadata, dataframes

    def _parse_metadata(self, file: TextIO) -> dict[str, Any]:
        """Help to parse metadata from the datafile.

        :param file: File object to read metadata from.

        :return: Metadata dictionary.
        """
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

            metadata.update(dict(zip(headers, values, strict=False)))
            file.seek(0)  # return cursor to the beginning

        return metadata
