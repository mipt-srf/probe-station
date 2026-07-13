"""Handler for capacitance-voltage (CV) sweep result analysis."""

from probe_station.analysis.common import find_x_at_max_y, get_y_at_x
from probe_station.analysis.handlers.base import BaseHandler


class Cv(BaseHandler):
    """Handler for capacitance-voltage sweep analysis.

    Provides methods for calculating dielectric constant, extracting
    permittivity at specific voltages, and plotting CV curves.
    """

    def calculate_epsilon(self) -> None:
        """Calculate dielectric constant. If area/thickness are not provided, use stored geometry set via set_geometry()."""
        epsilon0 = 8.854e-12
        area = self.parameters["area"]
        thickness = self.parameters["thickness"]
        self.data["Permittivity"] = self.data["Capacitance"] / epsilon0 / area * thickness

    def get_epsilon(self):
        if "Permittivity" in self.data:
            return self.data["Permittivity"]
        raise ValueError("Area and thickness must be set via set_geometry() before calculating epsilon")

    def get_field(self):
        """Return the electric field across the film (``Voltage / thickness``) in MV/cm.

        :return: The electric field for every measured point, in MV/cm.
        """
        thickness = self.parameters.get("thickness")
        if thickness is None:
            raise ValueError("Thickness must be set via set_geometry() before calculating the field")
        return self.data["Voltage"] / thickness * 1e-8  # V/m -> MV/cm

    def set_geometry(self, area: float, thickness: float) -> None:
        """Store sample geometry (area and thickness) on the handler and compute permittivity if possible."""
        self.parameters["area"] = area
        self.parameters["thickness"] = thickness

        self.calculate_epsilon()

    def plot(self) -> None:
        self.plot_base(
            self.data["Voltage"],
            self.data["Capacitance"],
            xlabel="Voltage",
            ylabel="Capacitance",
        )

    def plot_resistance(self) -> None:
        self.plot_base(
            self.data["Voltage"],
            self.data["Resistance"],
            xlabel="Voltage",
            ylabel="Resistance",
            color="tab:red",
        )

    def plot_epsilon(
        self,
        area: float | None = None,
        thickness: float | None = None,
        color: str | None = None,
        label: float | str | None = None,
        alpha: float | None = None,
        field: bool = True,
    ) -> None:
        """Plot dielectric constant against electric field, or against voltage when ``field`` is unset.

        :param field: If ``True`` (default), use electric field (``Voltage / thickness``, in MV/cm)
            on the x-axis; if ``False``, use voltage.
        """
        if area is not None and thickness is not None:
            self.set_geometry(area, thickness)

        epsilon = self.get_epsilon()
        if field:
            x_data = self.get_field()
            xlabel = "Electric field, MV/cm"
        else:
            x_data = self.data["Voltage"]
            xlabel = "Voltage, V"
        self.plot_base(
            x_data=x_data,
            y_data=epsilon,
            xlabel=xlabel,
            ylabel="Dielectric constant",
            label=label,
            color=color,
            alpha=alpha,
        )

    def get_epsilons_at_voltage(self, voltage: float, tolerance: float = 5e-2) -> tuple[float, float]:
        """Return the permittivity at the specified voltage for both forward and reverse sweeps.

        :param voltage: The voltage at which to get the permittivity.
        :param tolerance: Maximum allowed difference between target and actual voltage.
        :return: Tuple of (forward_epsilon, reverse_epsilon) at the specified voltage.
        """
        first_branch, second_branch = self.split_data()

        forward_epsilon = get_y_at_x(first_branch["Voltage"], first_branch["Permittivity"], voltage, tolerance)
        reverse_epsilon = get_y_at_x(second_branch["Voltage"], second_branch["Permittivity"], voltage, tolerance)

        return forward_epsilon, reverse_epsilon

    def get_coercive_voltage(self) -> tuple[float, float]:
        """Return the voltages at which the capacitance is the highest.

        :return: The forward- and reverse-sweep voltages at which the capacitance is the highest.
        """
        first_branch, second_branch = self.split_data()

        forward_coercive_voltage = find_x_at_max_y(first_branch["Voltage"], first_branch["Capacitance"])
        reverse_coercive_voltage = find_x_at_max_y(second_branch["Voltage"], second_branch["Capacitance"])

        return forward_coercive_voltage, reverse_coercive_voltage
