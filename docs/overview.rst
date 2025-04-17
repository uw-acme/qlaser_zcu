Introduction
=================

Purpose
---------------
Quantum computing is an advancing field that offers exponential speedups for problems that are difficult for classical computers to solve. One prominent platform for quantum computing utilizes trapped ions—charged atoms confined by electric fields and manipulated with lasers. Trapped ions provide high-fidelity quantum operations, long coherence times, and scalability potential. However, the complexity of the laser control system can be a bottleneck for the development of trapped-ion quantum computers. The hardware must generate multiple channels with precise timing and amplitude control to manipulate the ions. The control system must also be flexible to accommodate different experimental setups and be user-friendly to facilitate the demonstration of new quantum algorithms. This project aims to simplify the control system by providing a user-friendly interface to the FPGA-based laser control system. 

System Overview
------------------
The Qlaser-ZCU project consists of an :term:`FPGA` board (Xilinx ZCU102) that generates the laser control signals. The FPGA board interfaces with external digital-to-analog converters (:term:`DAC`) that converts the :term:`digital` signals to :term:`analog` signals. The signals are then sent to the laser control system to manipulate the trapped ions. The FPGA board has multiple :term:`channels` that can generate different waveforms and voltages to manipulate the ions. The user can configure the waveforms by defining various parameters. The FPGA generates the waveforms based on the user's configurations generated throught this package. 

.. _overview_diagram:
.. figure:: _static/diagrams/overview.jpg
    :align: center
    :width: 60%

    Overview of the hardware structure

