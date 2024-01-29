import re
from collections.abc import Iterable
from pathlib import Path
from typing import TextIO

import numpy as np
import pandas as pd


def parse_metadata(file: TextIO):
    lines = [line for line in file if not line.isspace()]  # drop empty lines
    metadata = {}
    for header_str, value_str in yield_pairs(lines):
        headers_pattern = r"\s*([A-Z][a-z]+(?: [a-zA-Z]+)*)"
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


def parse_datafile(path: Path):
    with open(path, "r") as file:
        metadata = parse_metadata(file)
        lines = file.readlines()
    data = [
        line.strip().split() for line in lines[len(metadata.keys()) + 2 :]
    ]  # TODO: change to len + 1 + PQPUND for versatility, check other modes
    df = pd.DataFrame(data[1:]).iloc[:, :3].dropna(how="all")
    df.columns = data[0]
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
    return metadata, *dataframes


def is_float(string: str):
    """Returns True if string is convertible to float, False otherwise"""
    try:
        float(string)
        return True
    except (ValueError, TypeError):  # str and None
        return False


def yield_pairs(lst: Iterable):
    """Yield pairs of elems from iterable and subscriptable object"""
    for pair in zip(lst[::2], lst[1::2]):
        yield pair


def non_numeric_row(df: pd.DataFrame):
    """Find index of first row with non-numerical values"""
    return np.argmin(df.map(is_float).all(axis=1))
