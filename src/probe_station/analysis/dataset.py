from pymeasure.experiment import (
    Results,
)

from probe_station._CV import CV
from probe_station._DC_IV import DC_IV
from probe_station.measurements.voltage_sweeps.CV.procedure import (
    CvSweepProcedure,
)
from probe_station.measurements.voltage_sweeps.IV.SMU.built_in_procedure import (
    IvSweepProcedure,
)


class Dataset(Results):
    def __new__(cls, filename):
        instance = Results.load(filename)
        instance.__class__ = cls  # Change the class to Dataset
        return instance

    def __init__(self, data_filename):
        # mappings for old processing routines
        mappings = {CvSweepProcedure: CV, IvSweepProcedure: DC_IV}
        self.handler_cls = mappings.get(self.procedure.__class__)

        self.data_cut = self.data[200:] if len(self.data) > 300 else self.data
        # Reset index for data_cut
        self.data_cut = self.data_cut.reset_index(drop=True)

        self.handler = self.handler_cls(
            metadata=self._convert_parameters(self.parameters),
            dataframes=[self._rename_data_columns(self.data_cut)],
        )

    def _convert_parameters(self, params):
        return {"Bias": params.get("first_voltage").value}

    def _rename_data_columns(self, df):
        if self.handler_cls == DC_IV:
            return df.rename(columns={"Voltage": "Bias", "Top electrode current": "Current"})
        return df
