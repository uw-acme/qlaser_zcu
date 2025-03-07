API Reference
=================
Main front-end tools
---------------------

.. automodule:: qlaser_zcu
    :members:

.. automodule:: qlaser_zcu.constants
    :members:

Functions and wrappers to interact with the FPGA.

.. automodule:: qlaser_zcu.genwave
    :members:
    

Barebone Class to interact directly with the FPGA
--------------------------------------------------

"Raw" class to interact with the FPGA. This class is can be used directly for more advanced or fine-grained usages. It is the base class for the :class:`QlaserFPGA` class.

.. autoclass:: qlaser_zcu.qlaser_fpga.QlaserFPGA()
   :members:

.. autoclass:: qlaser_zcu.qlaser_fpga.PulseConfig()
   :members: