"""Dataset wrapper around PyMeasure Results for analysis of new-format CSV files."""

from pymeasure.experiment import Results

from probe_station.analysis.handlers.cv import Cv
from probe_station.analysis.handlers.fet_ids_vds import FetIdsVds
from probe_station.analysis.handlers.forc import Forc
from probe_station.analysis.handlers.iv import Iv
from probe_station.analysis.matlab.dc_iv import DC_IV
from probe_station.measurements.cmu.cv_sweep import CmuCvSweepProcedure
from probe_station.measurements.pymeasure_base import load_results
from probe_station.measurements.smu.fet_ids_vds import SmuFetIdsVdsProcedure
from probe_station.measurements.smu.iv_sweep import SmuIvSweepProcedure
from probe_station.measurements.wgfmu.forc import WgfmuForcProcedure
from probe_station.measurements.wgfmu.iv_sweep import WgfmuIvSweepProcedure

# Explicit ``name -> class`` registry passed to ``load_results`` so files
# recorded as living in ``__main__`` (procedures run as a standalone script
# rather than launched in-process), which PyMeasure cannot rebuild from the
# header, reconstruct against a pinned class. Curated for backwards
# compatibility: map a recorded name here to keep loading legacy data even if
# the class is later renamed or moved.
_PROCEDURE_CLASSES = {
    cls.__name__: cls
    for cls in (
        CmuCvSweepProcedure,
        SmuIvSweepProcedure,
        WgfmuIvSweepProcedure,
        SmuFetIdsVdsProcedure,
        WgfmuForcProcedure,
    )
}


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
        instance = load_results(filename, procedure_classes=_PROCEDURE_CLASSES)
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
            WgfmuForcProcedure: Forc,
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
