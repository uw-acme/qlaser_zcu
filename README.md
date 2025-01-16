# Qlaser ZCU
Python package that interface with the NanoQ Laser hardware controller on an Xilinx ZCU102 FPGA board.

## Use
This repo has been setup as a python package. Simply install into your python environemnt with 
```
pip install git+https://https://github.com/uw-acme/qlaser_zcu.git
```
It is recommended to create a virtual environment with `python -m venv .venv` and install the package into that environment, as this project is in its very early development and many things are not set yet

## Develop
This repo/package is build with [Poetry](https://python-poetry.org/docs/). You may clone this repo into your devices and setup a development envireonment with `poetry install` command. This will craete a python environment and download all nessisary packages into the environment

To build a documentation, goto `docs` folder and run `make html` command. This will create a html documentation in `docs/build/html` folder. Open `index.html` file in a browser to view the documentation