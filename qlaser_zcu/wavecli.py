import os
import pandas as pd  # for CSV processing
from typing import Sequence
from .qlaser_fpga import QlaserFPGA, PulseConfig
from .constants import *
from loguru import logger

def get_wave_ids() -> list[int]:
    """Get all wave IDs from the database

    Returns:
        list[int]: List of wave IDs
    """
    df = pd.read_csv("data/wavetables.csv")
    return df.columns.astype(int).to_list() if not df.empty else []

def get_wave(waveid: int, port: str | None = None) -> list[int]:
    """Get a waveform from the database

    Args:
        waveid (int): Wave ID
        port (str | None, optional): Port to connect to FPGA. Defaults to None to auto-detect.

    Returns:
        list[int]: Wave values
    """
    df = pd.read_csv("data/wavetables.csv")
    
    if waveid not in df.columns.astype(int).to_list():
        logger.error(f"Waveform ID {waveid} not found in the database")
        raise ValueError(f"Waveform ID {waveid} not found in the database")
    
    start_addr = waveid & 0xFFFF
    length = waveid >> 16
    
    # read the waveform from the FPGA
    return QlaserFPGA(portname=port).read_wave_table(start_addr, length)

def get_defns(channel: int, port: str | None = None) -> list[PulseConfig]:
    """Get pulse definitions from a channel

    Args:
        channel (int): Channel number (0-31)
        port (str | None, optional): Port to connect to FPGA. Defaults to None to auto-detect.

    Returns:
        pd.DataFrame: Pulse definitions
    """
    fpga = QlaserFPGA(portname=port)
    fpga.chan_sel(channel)
    
    pdefs = fpga.read_pulse_defn()
    # convert the pulse definitions to a list of dictionaries
    pulse_defn = []
    for i in pdefs:
        if (sum(list(i.values())) == 0):  # zero entry, stop
            break
        pulse_defn.append(i)

    return pulse_defn

def enable_channels(channels: list[int], port: str | None = None):
    """Enable channels

    Args:
        channels (list[int]): List of channel numbers (0-31)
        port (str | None, optional): Port to connect to FPGA. Defaults to None to auto-detect.
    """
    QlaserFPGA(portname=port).chan_en(channels)

def add_wave(values: list[int], keep_previous: bool = True, port: str | None = None) -> int:
    """Load a wave into the FPGA

    Args:
        values (list[int]): Wave values, must be in integers between 0 and maximum DAC value. Note that numpy integer types are not supported.
        keep_previous (bool, optional): Keep previous wave table. Defaults to True.
        port (str | None, optional): Port to connect to FPGA. Defaults to None to auto-detect.

    Returns:
        int: Wave ID
    """
    fpga = QlaserFPGA(portname=port)
    
    if keep_previous:
        df = pd.read_csv("data/wavetables.csv").reset_index(drop=True)
        last_id = df.columns.astype(int).to_list()[-1]
    else:
        df = pd.DataFrame()
        logger.info("Clearing FPGA wave table")
        fpga.clear_wave_table()
        last_id = 0

    start_addr = (last_id & 0xFFFF) + (last_id >> 16)
    # offset the start address to be even
    start_addr = start_addr + (start_addr % 2)
    
    # Check overflow
    if start_addr + len(values) > C_LENGTH_WAVEFORM:
        logger.error(f"Waveform RAM overflow. Start address {start_addr} + length {len(values)} > {C_LENGTH_WAVEFORM}")
        raise MemoryError(f"Waveform RAM overflow. Start address {start_addr} + length {len(values)} > {C_LENGTH_WAVEFORM}")

    waveid = len(values) << 16 | start_addr

    data = pd.Series(values, name=waveid, dtype=int)
    df = pd.concat([df, data], axis=1)
    os.makedirs("data", exist_ok=True)  # Create data directory if it doesn't exist
    df.to_csv("data/wavetables.csv", index=False)
    
    fpga.write_wave_table(start_addr, values, all_chan=True)
    logger.debug(f"Wave {waveid} loaded into FPGA at address {start_addr}")
        
    return waveid

def set_defns(
    definitions: Sequence[PulseConfig],
    seq_length: int,
    channel: int,
    port: str | None = None,
    flush_type: str = "debug",
):
    """Load pulse definitions into the FPGA

    Args:
        definitions (DictLike): Wave definitions
        seq_length (int): Total duation to run for **all** channels
        channel (int): Channel (0-31) to load the wave(s) into.
        port (str | None, optional): Port to connect to FPGA. Defaults to None to auto-detect.
        reset (bool, optional): clear and reset the system. Defaults to False.
        flush_type (str, optional): FPGA seral output to log type. Either "info" or "debug". Defaults to "debug". 
    """
    # Make sure definitions param is a list
    if not isinstance(definitions, list):
        definitions = [definitions]
    
    fpga = QlaserFPGA(portname=port)
    
    fpga.set_seq(seq_length)
    fpga.chan_sel(channel)
    
    logger.info(f"Clearing FPGA pulse definition memory on channel {channel}")
    fpga.clear_ram_defn()
    fpga.print_all(type=flush_type)
    
    for i, entry in enumerate(definitions):
        logger.info(f"Loading wave {i} into FPGA")
        fpga.entry_pulse_defn(
            entry['wave_id'],
            entry['start_time'],
            entry['scale_gain'],
            entry['scale_addr'],
            entry['sustain'],
            n_entry = i
        )
    fpga.print_all(type=flush_type)  # flush output
    
    # export the definitions to a CSV file
    pd.DataFrame(definitions).to_csv(f"data/definitions_channel{channel}.csv", index=False)

def vdac_to_hex(voltage: float, vref: float = VOLTAGE_REF, vref_type: str = VREF_INTERNAL) -> int:
    """Convert voltage to PMOD DAC code. Useful for setting DAC values for the "DC" voltages through the PMODs

    Args:
        voltage (float): Voltage to convert
        vref (float, optional): Reference voltage. Defaults to `VOLTAGE_REF`.
        vref_type (str, optional): Reference voltage type. Defaults to `VREF_INTERNAL`.

    Returns:
        int: DAC value
    """
    # Limit input to be between zero and the reference voltage
    if ((vref_type == VREF_INTERNAL) and (voltage > (2.0 * vref))):
        logger.warning('Limiting max voltage to 2x internal vref: ' + str(2.0*vref))
        voltage = 2.0 * vref

    elif (vref_type == VREF_EXTERNAL) and (voltage > vref) :
        logger.warning('Limiting max voltage to ext ref : ' + str(vref))
        voltage = vref

    elif (voltage < 0) :
        logger.warning('Limiting min voltage to : 0.0')
        voltage = 0.0
        
    # Convert voltage to DAC setting
    if (vref_type == 'internal'):
        step = 2.0 * vref / (2.0 ** DAC_BITS_RES)
    else:
        step = vref / (2.0 ** DAC_BITS_RES)

    # Make DAC code
    dac_code = int(voltage/step)

    if (dac_code > (2** DAC_BITS_RES) - 1): 
        dac_code = (2**DAC_BITS_RES) - 1
        logger.warning('Limiting max dac_code to : ' + hex(dac_code))

    return dac_code