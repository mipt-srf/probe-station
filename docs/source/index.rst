.. _index:

######
|name|
######

Probe station package is a Python package that was developed in Shared Research Facilities (SRF) Center at Moscow Institute of Physics and Technology (MIPT) to simplify the process of running measurements with Keysight B1500 semiconductor parameter analyzer.

See :doc:`Installation <getting-started/installation>` page for instructions on how to install the package depending on your needs. If you want to look through the options provided by the package, and learn how to use them, see :doc:`Usage <getting-started/usage>` page. If you want to learn how the package is structured, see :doc:`Structure <learning-package/structure>` page. If you want to contribute, see :doc:`Contribution <contribution>` page. Finally, if you're interested in going in depths, there are some details about underlying libraries, hardware specifics as well as additional resources on the :doc:`Onboarding <onboarding>` page.

.. note:: 

   The documentation is mostly structured in accordance with https://diataxis.fr/. In short, there are 4 types of pages: tutorials, how-to guides, reference pages and explanation pages - each page is marked with a corresponding tag. The first 2 types describe **how to use** the package (action), while the last 2 types describe **how it works** (knowledge). On the other hand: tutorials and explanation pages are useful for **learning**, while how-to guides and reference pages are useful for **applying** the knowledge.

   .. image:: https://diataxis.fr/_images/diataxis.png

.. _learning-docs:

.. toctree::
   :maxdepth: 2
   :caption: Getting started

   getting-started/installation
   getting-started/usage
   getting-started/demos

.. toctree::
   :maxdepth: 1
   :caption: Tutorial
   :hidden:

   tutorial/writing-your-first-script
   tutorial/wrapping-into-procedure

.. toctree::
   :maxdepth: 2
   :caption: Learning package
   :hidden:

   learning-package/structure
   learning-package/hardware
   learning-package/why-not-raw-scpi
   learning-package/advanced-usage
   learning-package/dependencies
   learning-package/wgfmu
   explanation/connection
   explanation/b1500

.. toctree::
   :maxdepth: 1
   :caption: Reference
   :hidden:

   api
   reference/manuals

.. toctree::
   :maxdepth: 1
   :caption: Smth
   :hidden:

   contribution
   onboarding