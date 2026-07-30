############
How it works
############

Hardware
========

Agilent/Keysight B1500 is a semiconductor parameter analyzer. The main features of the device are:

* Modularity - the device has 10 slots for different units, which can be combined to perform different measurements.
* No re-cabling - the device has multiple switching units that allow to switch between units programmatically (link to section), without changing the cable configuration.

Each unit is inserted into a slot and connected to the mainframe (fig). All of the units except HPSMU (High Power SMU) take 1 slot, while HPSMU takes 2 slots. Each unit has 1 or 2 channels.

In our setup, there are following installed units:

* HV-SPGU (High Voltage Semiconductor Pulse Generator Unit)
* WGFMU (Waveform Generator/Fast Measurement Unit)
* HPSMU (High Power Source Measure Unit)
* HRSMU (High Resolution Source Measure Unit)
* HRSMU (High Resolution Source Measure Unit)
* MPSMU (Medium Power Source Measure Unit)
* MFCMU (Medium Frequency Capacitance Measurement Unit)

SMU, WGFMU, HV-SPGU has similar functionality but differ in characteristics and therefore are suited for different applications. Short summary of when to use which unit:

.. Table + summary

In short, you should use SMU if you're fine with measurement time per point >~ 30-100 ms1, WGFMU if you need to measure faster than that, but don't need high voltage, and HV-SPGU if you need to apply high voltage short pulses without current measuring.

Switching between units
-----------------------


Software
========

As with other instruments, B1500 can be controlled via SCPI commands. 

.. Про remote usb

Details
=======

To send a command for specific unit, you need to specify the slot number. E.g. to enable the output of 

SMU naming conventions
----------------------

SMU3, etc.

WGFMU specifics
---------------

Contrary to all other units, 

Under the hood, it also sends SCPI commands, but the formatting is a bit different. In general you can reverse engineer the commands using keysight IO. That will probably increase the speed of measurements for some cases. Additionally, that will probably allow you to use internal program memory for WGFMU commands as well that can be helpful when extremely small delays are required (e.g. if you need to measure retention on ucs scale after fast high-voltage write pulse produced by SPGU)

.. important::

    By default (e.g. after B1500 reset), the SMU/PGU output is disabled. Always remember to enable SMU output after the end of your measurements, so that people who don't know how to work with that, still can use SMUs without changing cables.