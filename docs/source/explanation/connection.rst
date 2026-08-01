##########
Connection
##########

VISA
====

`Virtual instrument software architecture (VISA) <https://en.wikipedia.org/wiki/Virtual_instrument_software_architecture>`_ is a standard API for working with measurement instruments. It allows instruments connected via different physical interfaces (GPIB, USB, Ethernet, etc.) to be controlled in the same way.

VISA itself is a specification. There are multiple implementations of VISA by different vendors, e.g. NI-VISA by National Instruments, Keysight VISA by Keysight Technologies, TekVISA by Tektronix, etc. There is also a open-source implementation of VISA called `PyVISA-py <https://pyvisa.readthedocs.io/projects/pyvisa-py/en/latest/index.html>`_, which is a pure Python implementation of VISA.

PyVISA
======

`PyVISA <https://pyvisa.readthedocs.io/en/latest/>`_ is a Python library that provides a way to communicate with instruments using any VISA implementation. Basically, it is a wrapper around VISA implementation (e.g. NI-VISA, Keysight VISA, PyVISA-py, etc.) that allows you to use VISA functionality from Python.

B1500
=====

B1500 itself is a Windows PC with measurement hardware - SMUs, CMU, etc. connected as USBTMC device. To communicate with hardware, we can use Keysight VISA implementation or PyVISA and send commands from the B1500 itself. However, this is not very convenient, so we want to communicate with B1500 from our PC.

Remote USB
==========

Keysight IO Libraries Suite has `Remote USB <https://helpfiles.keysight.com/IO_Libraries_Suite/English/IOLS_Windows/Connection_Expert_New/Content/Connection_Expert/HTML/Interfaces/Manage_RemoteUSBInterface.htm>`__ feature that allows you to use one PC as a `Remote IO Server <https://helpfiles.keysight.com/IO_Libraries_Suite/English/IOLS_Linux/IOLS/Content/ProgrammingGuide/Procedural_Topics/RemoteIoServerSoftwareOverview.htm>`_ and then connect to it from another PC using `Remote USB Interface <https://helpfiles.keysight.com/IO_Libraries_Suite/English/IOLS_Windows/Connection_Expert_New/Content/Connection_Expert/HTML/Interfaces/Manage_RemoteUSBInterface.htm>`_.

Our setup
=========

Physical and network layers
---------------------------

PC is connected to B1500 mainframe (through a router) by Ethernet. Next, there is a Remote USB interface based on proprietary Keysight SICL-LAN protocol on top of TCP/IP that allows you to send commands using another PC, not the B1500 itself. Next, there is USBTMC protocol that allows you to send commands to the measurement hardware connected to the mainframe via USB.

I/O layer
---------

PyVISA is used as a wrapper around Keysight VISA implementation to send commands using Python. Connection can be made using USB address of the hardware once the Remote USB interface is established in Keysight Connection Expert.

As a result, because Keysight Remote USB interface hides the remoteness of the connection, it looks like we are sending commands to the instrument connected to our PC via USB, while in fact the commands are sent to the B1500 mainframe over TCP/IP and then to the measurement hardware connected to the mainframe over USB.