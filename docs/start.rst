Installing the package
----------------------

Install Directly from Git+Pip (Recommended)
===========================================

First, you need to install the package. You can do this by running the following command:

.. code-block::
    
    $ pip install git+https://github.com/uw-acme/qlaser_zcu.git

This command should install all the dependencies required to run the package. It was been tested with Python 3.11.
It is recommended to use a virtual environment to avoid conflicts with other packages. You can create a virtual environment using the following command:

.. code-block::

    $ python -m venv .venv
    $ source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`

Build from Source
==================

Clone the `package from the repository <https://github.com/uw-acme/qlaser_zcu.git>`_. Then build with `Poetry <https://python-poetry.org/>`_ with :code:`poetry install` command. Refer to the `Poetry documentation <https://python-poetry.org/docs/>`_ for more information on how to setup the environment and build the package.

Setup the hardware
-------------------

Download the hardware binary (BOOT.bin) from `the repository <https://github.com/uw-acme/NANO_QLASER.git>`_ to an SD card. Insert the SD card into the ZCU102 board and power it on. The FPGA will automatically load the binary from the SD card.

.. warning::
    Make sure to use the correct version of the hardware binary that matches the version of the software package. Using an incompatible version may result in unexpected behavior or errors. :mod:`~qlaser_zcu.qlaser_fpga.QlaserFPGA` class will check the versions of the hardware binary and raise an error if it is incompatible upon initialization.

Then connect all the peripherals to the ZCU102 board as described in :numref:`overview_diagram`. Connect the USB cable to the UART port on the ZCU102 board and the other end to your computer. This will allow you to communicate with the FPGA using the serial interface from a PC with this package installed. :mod:`~qlaser_zcu.qlaser_fpga.QlaserFPGA` class could self-detect the serial port and connect to it automatically. You may specify the port name as an argument manually when initializing the class. You could also manually use :meth:`~qlaser_zcu.qlaser_fpga.QlaserFPGA.versions` to check the version and connectivity.

.. note::
    The UART on the ZCU102 board uses `Silicon Labs Quad CP2108 USB to UART Bridge`. You may need to install additional driver for your operating system.

Then you may use the package to communicate with the FPGA and generate pulsed waveform. For example:

.. note::
    Most :mod:`~qlaser_zcu.wavecli` functions will initilize the :mod:`~qlaser_zcu.qlaser_fpga.QlaserFPGA` class internally in order to communicate with the FPGA.

.. _example:
.. code-block:: python

    from qlaser_zcu.wavecli import *  # Front-end interface to convert user-defined waveform data and pulse parameters into addressable instructions
    from qlaser_zcu.qlaser_fpga import QlaserFPGA  # the class that wraps the communication with the FPGA
    from loguru import logger  # a nice logging for debugging and development purpose

    # add some waves
    wave0 = add_wave([1,2,3,4,5], keep_previous=False)
    wave1 = add_wave([6,7,8])
    wave2 = add_wave([11,12,13,14,15,16,17,18,19,20])

    # define some pulse definitions
    dfn = [{
            "wave_id": wave0,
            "start_time": 5,
            "scale_gain": 1.0,
            "scale_time": 1.0,
            "sustain": 5
        },
        {
            "wave_id": wave1,
            "start_time": 128,
            "scale_gain": 1.0,
            "scale_time": 1.0,
            "sustain": 5
        },{
            "wave_id": wave2,
            "start_time": 256,
            "scale_gain": 1.0,
            "scale_time": 1.0,
            "sustain": 5
        }
    ]

    sequence_len = 1872  #1.872us
    set_defns(dfn, sequence_len, 0)
    enable_channels(0)

    # read back the pulse definitions
    logger.info(get_defns(0))
    # read back the wave table
    logger.info(get_wave(wave0))
    logger.info(get_wave(wave1))
    logger.info(get_wave(wave2))

    # additional ways to interfacte with the FPGA
    hw = QlaserFPGA()
    hw.read_errs()
    hw.write_dc_chan(0, 1234)  # write DC channel 0 with value 1234 (out of 4096 dac values)

Plese refer to the :ref:`API documentation <api>` for more information.