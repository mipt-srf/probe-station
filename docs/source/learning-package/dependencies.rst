############
Dependencies
############

The B1500 class heavily depends on 2 main sources:

Pymeasure package that contains a lot of different drivers for SCPI instruments, including B1500.

keysight-b1530a library that contains functionality for WGFMU. Since it's based on compiled .dll library that is platform-specific, it's placed as a separate repository

The custom B1500 class in this package is basically a wrapper around main AgilentB1500 class from pymeasure that is combined with WGFMU class from keysight-b1530a. There are also some opinion-based customizations made for convenient usage specifically at mipt-srf probe stations.

.. _pymeasure-agilentb1500:

Pymeasure's AgilentB1500 class
==============================

.. _keysight-b1530a:

keysight-b1530a
===============