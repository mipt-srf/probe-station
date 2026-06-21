"""Sweep-mode enum for the SMU staircase-sweep procedures."""

from enum import IntEnum


class SmuSweepMode(IntEnum):
    """How the SMU staircase voltage sweep is structured."""

    # Sweep straight between the two set voltages: start -> stop -> start.
    START_TO_STOP = 1
    # Sweep each polarity out from zero: 0 -> start -> 0, then 0 -> stop -> 0.
    FROM_ZERO = 2
