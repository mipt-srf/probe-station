###############
B1500 specifics
###############

There are a few things that are specific to Agilent B1500 and might be confusing if you are used to other instruments. This section is intended to clarify these specifics.

FLEX commands
=============

The instrument uses FLEX (Fast Language for EXecution) commands to control the instrument (see `Programming Guide page 1-22 <programming-guide>`). Countrary to SCPI commands, they do not have a tree-like structure, but rather use a flat structure where each command consists of unique combination of letters.

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item::

      .. figure:: https://dl.cdn-anritsu.com/en-us/test-measurement/ohs/10450-00061D/ProgrammingManual/images/SCPI.3.3.2.jpg
         :alt: A typical SCPI command tree, with commands nested under subsystems

         **SCPI.** Commands are nested under subsystems, so a full command is a
         path down the tree.

   .. grid-item::

      .. figure:: images/flex-command-list.png
         :alt: An excerpt from the FLEX command index, a flat alphabetical list

         **FLEX.** Commands are a flat alphabetical list, each one a unique
         combination of letters.

Quering
-------

Querying the instrument is also different from common SCPI commands. Instead of adding ``?`` to the end of the command, most of the queries are made using ``*LRN?`` command, which returns the settings for specified type of query response.

.. seealso::

   :ref:`Querying <learning-package/b1500-class:querying>` for explaination of how querying logic is implemented in Pymeasure and how to use it in practice.

   :ref:`Programming Guide page 4-129 <programming-guide>` for details on ``*LRN?`` command.

Connection
==========

Most of the time instruments are connected to the computer via USB or LAN directly or through a switch. Then, the connection is established using the address of the instrument. So, if the instrument is connected via Ethernet, the address will be something like ``TCPIP0::192.168.1.100::INSTR`` and so on. In case of B1500, the connection is established through a Keysight Remote USB interface, so the address will look like a USB address, even if the instrument is in fact connected via Ethernet. See :ref:`Connection <explanation/connection:b1500>` page for more details.