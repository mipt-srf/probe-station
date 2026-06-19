"""Dataset wrapper around PyMeasure Results for analysis of new-format CSV files."""

import re

from pymeasure.experiment import Results

from probe_station.analysis.handlers.cv import Cv
from probe_station.analysis.handlers.fet_ids_vds import FetIdsVds
from probe_station.analysis.handlers.iv import Iv
from probe_station.analysis.matlab.dc_iv import DC_IV
from probe_station.measurements.cmu.cv_sweep import CmuCvSweepProcedure
from probe_station.measurements.smu.fet_ids_vds import SmuFetIdsVdsProcedure
from probe_station.measurements.smu.iv_sweep import SmuIvSweepProcedure
from probe_station.measurements.wgfmu.iv_sweep import WgfmuIvSweepProcedure

# Procedure classes keyed by their bare name.  Used to reconstruct procedures
# recorded as living in ``__main__`` -- i.e. run as a standalone script rather
# than launched in-process -- which PyMeasure cannot rebuild from the header.
_PROCEDURE_CLASSES = {
    cls.__name__: cls
    for cls in (CmuCvSweepProcedure, SmuIvSweepProcedure, WgfmuIvSweepProcedure, SmuFetIdsVdsProcedure)
}


def _read_procedure_name(filename):
    """Return the bare procedure class name recorded in a result file's header."""
    with open(filename, encoding=Results.ENCODING) as f:
        for line in f:
            if not line.startswith(Results.COMMENT):
                break
            stripped = line[1:].strip()
            if stripped.startswith("Procedure:"):
                match = re.search(r"<(?:.*\.)?(?P<class>[^.>]+)>", stripped)
                if match:
                    return match.group("class")
    return None


def _load_results(filename):
    """Load a PyMeasure ``Results`` object, tolerating procedures run outside the launcher.

    PyMeasure can only reconstruct a procedure whose recorded module exposes the
    class.  Procedures run directly from a script or notebook are recorded as
    living in ``__main__``, so the reconstruction raises ``AttributeError`` (or
    ``ImportError``).  In that case we look the class up by name and load again
    with the correct procedure class.
    """
    try:
        return Results.load(filename)
    except (AttributeError, ImportError):
        procedure_cls = _PROCEDURE_CLASSES.get(_read_procedure_name(filename))
        if procedure_cls is None:
            raise
        return Results.load(filename, procedure_class=procedure_cls)


class Dataset(Results):
    """Load a PyMeasure CSV result file and attach the appropriate analysis handler.

    The handler is chosen automatically based on the procedure class stored in
    the CSV metadata.  Attribute look-ups are forwarded to the handler, so
    ``ds.plot()`` works directly.
    """

    def __new__(cls, filename):
        """Create a new Dataset by loading a PyMeasure CSV file.

        :param filename: Path to the ``.csv`` result file.
        """
        instance = _load_results(filename)
        instance.__class__ = cls  # Change the class to Dataset
        return instance

    def __init__(self, data_filename):
        """Initialise handler based on the procedure that produced the data.

        :param data_filename: Path to the ``.csv`` result file.
        """
        self.data_cut = self.data[200:] if len(self.data) > 300 else self.data
        # Reset index for data_cut
        self.data_cut = self.data_cut.reset_index(drop=True)

        # mappings for old processing routines
        old_mappings = {SmuIvSweepProcedure: DC_IV}
        self.handler_cls = old_mappings.get(self.procedure.__class__)

        if self.handler_cls is not None:
            self.handler = self.handler_cls(
                metadata=self._convert_parameters(self.parameters),
                dataframes=[self._rename_data_columns(self.data_cut)],
            )
            return
        new_mappings = {
            CmuCvSweepProcedure: Cv,
            WgfmuIvSweepProcedure: Iv,
            SmuFetIdsVdsProcedure: FetIdsVds,
        }
        self.handler_cls = new_mappings.get(self.procedure.__class__)

        if self.handler_cls is None:
            raise ValueError(f"Unsupported procedure class: {self.procedure.__class__}")

        self.handler = self.handler_cls(parent=self)

    def __getattr__(self, name):
        if hasattr(self, "handler") and hasattr(self.handler, name):
            return getattr(self.handler, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _convert_parameters(self, params):
        return {"Bias": params.get("first_voltage").value}

    def _rename_data_columns(self, df):
        if self.handler_cls == DC_IV:
            return df.rename(columns={"Voltage": "Bias", "Top Electrode Current": "Current"})
        return df
