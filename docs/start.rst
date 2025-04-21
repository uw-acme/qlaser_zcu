Installing the package
----------------------
First, you need to install the package. You can do this by running the following command:

.. code-block::
    
    $ pip install git+https://https://github.com/uw-acme/qlaser_zcu.git

It is recommended to use a virtual environment to avoid conflicts with other packages. You can create a virtual environment using the following command:

.. code-block::

    $ python -m venv venv
    $ source venv/bin/activate  # On Windows use `venv\Scripts\activate`



.. TODO: add how to get the hardware binary and how to load it on the FPGA. also warn user about version mismatch.

Setup the hardware
-------------------

Download the hardware binary (BOOT.bin) from `the repository <https://github.com/uw-acme/NANO_QLASER.git>`_ to an SD card. Insert the SD card into the ZCU102 board and power it on. The FPGA will automatically load the binary from the SD card.

.. warning::
    Make sure to use the correct version of the hardware binary that matches the version of the software package. Using an incompatible version may result in unexpected behavior or errors.

Then connect all the peripherals to the ZCU102 board as described in :numref:`overview_diagram`. Connect the USB cable to the UART port on the ZCU102 board and the other end to your computer. This will allow you to communicate with the FPGA using the serial interface from a PC with this package installed.

.. note::
    The UART on the ZCU102 board uses `Silicon Labs Quad CP2108 USB to UART Bridge`. You may need to install additional driver for your operating system.

Then you may use the package to communicate with the FPGA and generate pulsed waveform. For example:

.. _example:
.. code-block:: python

    from qlaser_zcu.wavecli import *
    from qlaser_zcu.qlaser_fpga import QlaserFPGA
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
