# Qlaser ZCU
Python package that interfaces with the NanoQ Laser hardware controller on an Xilinx ZCU102 FPGA board.

## Use
This repo has been set up as a Python package. All its dependencies should be able to resolve themselves using `pip`. Install into your Python (3.11 and up) environment with 
```
pip install git+https://github.com/uw-acme/qlaser_zcu.git
```
It is recommended to create a virtual environment with `python -m venv .venv` and install the package into that environment, as this project is in its very early development, and many things are not set yet

## Develop
This repo/package is built with [Poetry](https://python-poetry.org/docs/). You may clone this repo onto your devices and set up a development environment with the  `poetry install` command. This will create a Python environment and download all necessary packages into the environment

To build the documentation, go to the `docs` folder and run the `make html` command. This will create an HTML documentation in the `docs/build/html` folder. Open the `index.html` file in a browser to view the documentation
