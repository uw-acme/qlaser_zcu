import numpy as np
from typing import Sequence
from .qlaser_fpga import QlaserFPGA, PulseConfig
from loguru import logger

C_BITS_ADDR_WAVE = 12
MAX_WAVES = 4096


def poly_gen_numpy(
    degrees: int,
    time: float, 
    coeff: list
) -> float:
    """Numpy vectorized version of polynomial generator

    Args:
        degrees (int): Degree of polynomial
        time (float): Time value (x) to evaluate polynomial
        coeff (list): Coefficients of polynomial

    Returns:
        float: Polynomial value at given time point
    """
    powers = np.arange(1, degrees + 1)
    poly_sum = np.sum(np.array(coeff, dtype=np.float64) * (time ** powers))
    
    return (poly_sum / (degrees + 1)) * (2 ** (C_BITS_ADDR_WAVE - 1))

def calculate_pulse_value(
    current_time: int,
    start_time: int,
    pulse_time: int,
    time_factor: float,
    pulse_delay: int,
    gain_factor: float,
    coefficients: list
) -> float:
    """Calculate pulse value at given time point

    Args:
        current_time (int): Current time point
        start_time (int): Start time point of pulse
        pulse_time (int): Total numbers of durations/step of pulse's rise edge
        time_factor (float): Time factor (step size) to scale time
        pulse_delay (int): Sustain time after pulse rise edge and before fall edge
        gain_factor (float): Gain factor to scale wave value
        coefficients (list): Coefficients of polynomial

    Returns:
        float: Value of a polynomial at given time point
    """
    rel_time = current_time - start_time
    pulse_width = np.ceil((pulse_time - 1) / time_factor)
    x_processed = 0
    
    if 0 <= rel_time < pulse_width:
        # Rising edge
        x_processed = rel_time * time_factor
        
    elif pulse_width <= rel_time < (pulse_width + pulse_delay):
        # Hold at peak
        x_processed = pulse_time - 1
        
    elif (pulse_width + pulse_delay) <= rel_time < (2 * pulse_width + pulse_delay - 1):
        # Falling edge
        x_processed = (2 * pulse_width + pulse_delay - rel_time - 1) * time_factor
        
    else:
        x_processed = 0
        
    # Calculate wave value using polynomial
    return poly_gen_numpy(
            len(coefficients),
            x_processed / pulse_time,
            coefficients
            ) * gain_factor

def load_waves(
    definitions: Sequence[PulseConfig],
    seq_length: int,
    port: str | None = None,
    channel: int | None = None,
    time_type: str = "relative",
    reset: bool = True,
    flush_type: str = "debug",
    trigger: bool = False
):
    """Load a bunch of waves into the FPGA

    Args:
        definitions (Sequence[PulseConfig]): Wave definitions
        seq_length (int): Total duation to run for all channels
        port (str | None, optional): Port to connect to FPGA. Defaults to None to auto-detect.
        channel (int | None, optional): Channel to load the wave(s) into. Defaults to None to select all channels.
        time_type (str, optional): Time type to use for wave definitions. Either "relative" for timing related to start of each pulse or "absolute" for exact start time. Defaults to "relative".
        reset (bool, optional): oft reset values in the FPGA into known states. Defaults to True.
        flush_type (str, optional): FPGA seral output to log type. Defaults to "debug".
        trigger (bool, optional): Trigger the wave(s) after loading. Defaults to False.
    """
    # Make sure definitions param is a list
    if not isinstance(definitions, list):
        definitions = [definitions]
    
    fpga = QlaserFPGA(portname=port)
    if reset:
        fpga.reset(flush_type=flush_type)
    
    fpga.sel_pulse(seq_length)
    fpga.sel_channel(channel)
    fpga.print_all(type=flush_type)
    
    for entry in range(len(definitions)):
        logger.info(f"Loading wave {entry} into FPGA")
        if time_type == "relative" and entry > 0:
            start_time = definitions[entry - 1]["start_time"] + 2 * definitions[entry]["wave_len"] + definitions[entry]["sustain"] + definitions[entry]["start_time"]
        elif time_type == "absolute" or (time_type == "relative" and entry == 0):
            start_time = definitions[entry]["start_time"]
        else:
            ValueError(f"{time_type} is not either 'relative' or 'absolute'")
            
        fpga.entry_pulse_defn(
            entry,
            start_time,
            definitions[entry]["start_addr"],
            definitions[entry]["wave_len"],
            definitions[entry]["gain_factor"],
            definitions[entry]["scale_addr"],
            definitions[entry]["sustain"]
        )
        raw_table = []
        for i in range(definitions[entry]["wave_len"]):
            nval = int(poly_gen_numpy(len(definitions[entry]["coefficents"]), i / definitions[entry]["wave_len"], definitions[entry]["coefficents"]))
            if nval < 0:
                nval = 0  # pad negative numbers with 0
            raw_table.append(nval)
        
        fpga.write_wave_table(definitions[entry]["start_addr"], raw_table)
    
    fpga.print_all(type=flush_type)  # flush output
    if trigger:
        fpga.pulse_trigger()
