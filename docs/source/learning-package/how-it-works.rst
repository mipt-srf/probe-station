Software
========

.. Про remote usb

Details
=======

To send a command for specific unit, you need to specify the slot number. E.g. to enable the output of 

WGFMU specifics
---------------

Contrary to all other units, 

Under the hood, it also sends FLEX commands, but the formatting is a bit different. In general you can reverse engineer the commands using keysight IO. That will probably increase the speed of measurements for some cases. Additionally, that will probably allow you to use internal program memory for WGFMU commands as well that can be helpful when extremely small delays are required (e.g. if you need to measure retention on ucs scale after fast high-voltage write pulse produced by SPGU)

.. important::

    By default (e.g. after B1500 reset), the SMU/PGU output is disabled. Always remember to enable SMU output after the end of your measurements, so that people who don't know how to work with that, still can use SMUs without changing cables.

Switching between units
-----------------------