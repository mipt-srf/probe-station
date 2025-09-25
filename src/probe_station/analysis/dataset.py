from pymeasure.experiment import Results

from probe_station._DC_IV import DC_IV
from probe_station.analysis.handlers.cv import Cv
from probe_station.analysis.handlers.iv import Iv
from probe_station.measurements.voltage_sweeps.CV.procedure import CvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_procedure import IvSweepProcedure
from probe_station.measurements.voltage_sweeps.IV.WGFMU.procedure import WgfmuIvSweepProcedure


class Dataset(Results):
    def __new__(cls, filename):
        instance = Results.load(filename)
        instance.__class__ = cls  # Change the class to Dataset
        return instance

    def __init__(self, data_filename):
        self.data_cut = self.data[200:] if len(self.data) > 300 else self.data
        # Reset index for data_cut
        self.data_cut = self.data_cut.reset_index(drop=True)

        # mappings for old processing routines
        old_mappings = {IvSweepProcedure: DC_IV}
        self.handler_cls = old_mappings.get(self.procedure.__class__)

        if self.handler_cls is not None:
            self.handler = self.handler_cls(
                metadata=self._convert_parameters(self.parameters),
                dataframes=[self._rename_data_columns(self.data_cut)],
            )
            return
        new_mappings = {CvSweepProcedure: Cv, WgfmuIvSweepProcedure: Iv}
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
            return df.rename(columns={"Voltage": "Bias", "Top electrode current": "Current"})
        return df
