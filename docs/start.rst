Getting Started
---------------
First, you need to install the package. You can do this by running the following command:

.. code-block::
    
    $ pip install git+https://https://github.com/uw-acme/qlaser_zcu.git


Then, you can use the package by importing it in your Python code. For exmaple:

.. code-block:: python

    import sys
    from qlaser_zcu.genwave import load_waves
    from loguru import logger  # a nice logging for debugging and development purpose

    # Define the wave parameters. You may need to keep track of this to avoid conflicts
    start_time = 5
    start_addr = 0
    size = 180
    sustain = size*2

    # Fist wave, a third order polynomial
    pd = {
        "start_time": start_time,
        "start_addr": start_addr,
        "wave_len": size,
        "gain_factor": 1.0,
        "scale_addr": 1.0,
        "sustain": sustain,
        "coefficents": [1, 0, -1/6]
    }

    # Second wave, an linear wave
    pd2 = {
        "start_time": 4,
        "start_addr": 6,
        "wave_len": size,
        "gain_factor": 1.0,
        "scale_addr": 1.0,
        "sustain": sustain,
        "coefficents": [1.0]
    }

    # Load the waves into FPGA using QlaserFPGA. Refer to API doc for more details
    load_waves([pd, pd2], 1872, channel=1, trigger=True)
