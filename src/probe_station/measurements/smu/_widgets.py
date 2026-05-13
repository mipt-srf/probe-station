"""Custom plot widget with log-scale toggle for IV curve measurements."""

import numpy as np
import pyqtgraph as pg
from pymeasure.display.curves import ResultsCurve
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.widgets import PlotWidget


class AbsResultsCurve(ResultsCurve):
    """ResultsCurve that applies abs() to Y data when log_mode is enabled."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_mode = False

    def update_data(self):
        if self.force_reload:
            self.results.reload()
        data = self.results.data
        y_data = np.abs(data[self.y]) if self.log_mode else data[self.y]
        self.setData(data[self.x], y_data)


class IvPlotWidget(PlotWidget):
    """PlotWidget with a log-scale toggle checkbox for IV curve plots.

    When log scale is enabled the Y-axis switches to log10 and all curves
    display abs(I) so that negative current values remain visible.
    """

    def _setup_ui(self):
        super()._setup_ui()
        self.log_scale_checkbox = QtWidgets.QCheckBox("Log scale")
        self.log_scale_checkbox.toggled.connect(self._toggle_log_scale)

    def _layout(self):
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(0)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setSpacing(10)
        hbox.setContentsMargins(-1, 6, -1, 6)
        hbox.addWidget(self.columns_x_label)
        hbox.addWidget(self.columns_x)
        hbox.addWidget(self.columns_y_label)
        hbox.addWidget(self.columns_y)
        hbox.addWidget(self.log_scale_checkbox)

        vbox.addLayout(hbox)
        vbox.addWidget(self.plot_frame)
        self.setLayout(vbox)

    def new_curve(self, results, color=pg.intColor(0), **kwargs):
        if "pen" not in kwargs:
            kwargs["pen"] = pg.mkPen(color=color, width=self.linewidth)
        if "antialias" not in kwargs:
            kwargs["antialias"] = False
        curve = AbsResultsCurve(
            results,
            wdg=self,
            x=self.plot_frame.x_axis,
            y=self.plot_frame.y_axis,
            **kwargs,
        )
        curve.setSymbol(None)
        curve.setSymbolBrush(None)
        curve.log_mode = self.log_scale_checkbox.isChecked()
        return curve

    def _toggle_log_scale(self, enabled):
        self.plot.setLogMode(x=False, y=enabled)
        for item in self.plot.items:
            if isinstance(item, AbsResultsCurve):
                item.log_mode = enabled
                item.update_data()
