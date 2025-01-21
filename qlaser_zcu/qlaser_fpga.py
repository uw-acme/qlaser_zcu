import serial
import serial.tools.list_ports
from serial.serialutil import SerialException
from typing import TypedDict
from loguru import logger

C_BITS_ADC = 12
C_BITS_ADDR_WAVE = 16
C_BITS_GAIN_FACTOR = 16
C_BITS_TIME_FACTOR = 16
C_MAX_CHANNELS = 32
C_ERR_BITS = 8
BIT_FRAC = 8
BIT_FRAC_GAIN = C_BITS_GAIN_FACTOR - 1
PULSE_START_MIN = 4  # Minimum start time for pulse

class PulseConfig(TypedDict):
    start_time: int
    start_addr: int
    wave_len: int
    scale_gain: float
    scale_addr: float
    sustain: int
    coefficents: list[int]

class QlaserFPGA:
    """Class to interact with the ZCU FPGA over serial port"""
    def __init__(self, portname : str=None, baudrate: int=115200):
        """Interact with the ZCU FPGA over serial port

        Args:
            portname (str, optional): Serial port to FPGA. Defaults to None to automatically select.
            baudrate (int, optional): Baudrate of the serial interface. Defaults to 115200.

        Raises:
            SerialException: No valid UART COM port found or given
        """
        self.logger = logger
                
        comlist = (list(serial.tools.list_ports.comports()))
        if portname:
            self.ser = serial.Serial(
                port = portname,\
                baudrate=baudrate,\
                parity=serial.PARITY_NONE,\
                stopbits=serial.STOPBITS_ONE,\
                bytesize=serial.EIGHTBITS,\
                timeout=1)
        elif len(comlist) > 0:
            for i in comlist:
                if "Interface 0" in i.description:        
                    portname = i[0]
                    break
            else:
                raise SerialException("No valid UART COM port found")
            self.ser = serial.Serial(
                port = portname,\
                baudrate=115200,\
                parity=serial.PARITY_NONE,\
                stopbits=serial.STOPBITS_ONE,\
                bytesize=serial.EIGHTBITS,\
                timeout=1)
            self.logger.debug(f"Found and connected to serial port: {portname}")
        else:
            raise SerialException("No ports found or given!")
        
        # Turn off command echo
        self.ser.write('0e'.encode('utf-8'))
        
    
    def print_all(self, errors: str = "ignore", type="info"):
        """Read and print all data from the serial port

        Args:
            errors (str, optional): How errors are handled when decoding the serial message. Defaults to "ignore".
            type (str, optional): Type of log message. Either "info" or "debug". Defaults to "info".
        """
        while True:
            data = self.ser.readline()
            if not data:
                break
            # logger.info(data.decode('utf-8', errors=errors))
            eval(f"self.logger.{type}")(data.decode('utf-8', errors=errors))

    def reset(self, flush_type: str="debug"):
        """Soft reset data in the FPGA and reset pulse entry counter to 0
        
        Args:
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
        """
        self.ser.write(b'\x52')
        self.logger.debug("Sent soft reset command to FPGA")
        # give fake values to all channel's first entry to ensure no register is left with garbage
        self.sel_channel(channel=None)
        self.entry_pulse_defn(0, 0xFFFFFF, 0, 2, 1.0, 1.0, 0)  # set to the end of the time... TODO: temporary solution
        self.print_all(type=flush_type)  # Clear the buffer
        
    def __gpo_rd(self, format_spec="08x") -> str:
        """Read the general purpose output register
        
        Used (almost) internally only

        Args:
            format_spec (str, optional): String format to be output. Defaults to "08x".

        Returns:
            str: Value of the general purpose output register
        """
        self.print_all(type="debug")  # Clear the buffer
        self.ser.write(b'r')
        # This command is also used for real-time serial debug, with format of <some string message>: 0x<value>
        # Strip it to get the value
        data = self.ser.readline().decode('utf-8', errors="replace").strip().split("0x")
        return format(int(data[1], 16), format_spec)
    
    def read_errs(self) -> tuple[str, str]:
        """Read the error registers.
        For now only Channel 1 and 2 are supported.

        Returns:
            tuple[str, str]: Error registers
        """
        err_lo = self.__gpo_rd()[-2:]
        err_hi = self.__gpo_rd()[-4:-2]
        
        return format(int(err_hi, 16), f"0{C_ERR_BITS}b"), format(int(err_lo, 16), f"0{C_ERR_BITS}b")

    def pulse_trigger(self, flush_type: str = "debug"):
        """Tell FPGA to start the pulse sequence
        
        Args:
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
        """
        self.ser.write(b't')
        self.logger.debug("Sent trigger command to FPGA")
        self.print_all(type=flush_type)

    def sel_pulse(self, seq_length: int, flush_type: str = "debug", channel: int | None = None):
        """Set the pulse sequence length

        Args:
            seq_length (int): Total duration of the pulse sequence
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
        """
        self.ser.write(f'{seq_length}sC'.encode('utf-8'))
        self.print_all(type=flush_type)

    def sel_channel(self, channel: int | None = None):
        """Select the channel to configure

        Args:
            channel (int, optional): Channel to configure. Defaults to None to select all channels.
        """
        if channel is not None and (channel > C_MAX_CHANNELS or channel < 1):
            raise ValueError(f"Channel {channel} is out of range")
        if channel is None:
            channel = 99
        self.ser.write(f'{channel}c'.encode('utf-8'))
        
    def write_wave_table(self, start_addr: int, values: list[int]):
        """Write a list of values pairs to the wave table starting at the given even-numbered address.

        Args:
            start_addr (int): Starting address of the wave table
            values (list[int]): List of values to be written
        """
        if bool(start_addr % 2):
            self.logger.error("Start address must be even!")
            return
        for i in range(start_addr, start_addr + len(values) - 1, 2):
            self.write_waves(i, values[i-start_addr], values[i-start_addr+1])

    def write_waves(self, addr: int, val16_lo: int, val16_up: int):
        """Write to wave table with fix-size of 2 values at given even-numbered address.

        Args:
            addr (int): Starting address of the wave table the data should be written to. 
            val16_lo (int): First value to be written
            val16_up (int): Second value to be written
        Examples:
            Write value 6 and 7 starting at address 6
            >>> write_waves(6, 6, 7)
        """
        addr32 = addr // 2
        if bool(addr % 2):
            self.logger.warning(f"Address {addr} is not even. Values may not be written correctly!")
        self.ser.write(str(val16_up * 2**C_BITS_ADDR_WAVE + val16_lo).encode('utf-8') + b'\xDD')
        self.ser.write(str(addr32).encode('utf-8') + b'\x9A')
        
    def read_waves(self, addr: int) -> tuple[int, int]:
        """Read a chunk/pair of values from the wave table with a even-numbered start address

        Args:
            addr (int): Starting address of the wave table the data should be read from.
        
        Returns:
            tuple[int, int]: Two 16-bit values read from the wave table. First one is the bottom 16 bits, second one is the top 16 bits.
        """
        addr32 = addr // 2
        self.ser.write(str(addr32).encode('utf-8') + b'\xBA')
        data = self.ser.readline().decode('utf-8', errors="replace").strip()
        return int(data) & 0xFFFF, int(data) >> 16

    def entry_pulse_defn(self,
                        n_entry: int,
                        n_start_time: int,  # minimum is 4
                        n_wave_addr: int,
                        n_wave_len: int,
                        n_scale_gain: float,
                        n_scale_addr: float,
                        n_flattop: int) -> None:
        """Write pulse parameters to the FPGA.
        Prints warnings if parameters exceed certain limits and
        Whenever this function gets called, a entry pointer increments by 1.

        Args:
            n_entry (int): Nth pulse entry. This value should and only be incremented by 1 every time this function is called.
            n_start_time (int): Starting time of the pulse. There need to be at least 4 time units before each pulse starts.
            n_wave_len (int): Duration of the rise of the pulse, unscaled.
            n_scale_gain (float): Amplitude scaling factor of the pulse. This value should always be any decimals between (0, 1].
            n_scale_addr (float): Time scale factor of the pulse. This value should always be any decimals between [1, wave_len).
            n_flattop (int): Sustain duration (whatever stays flat between rise and fall) of the pulse.
        """
        n_scale_gain = int(n_scale_gain * 2**BIT_FRAC_GAIN)
        n_scale_addr = int(n_scale_addr * 2**BIT_FRAC)
        
        # Check bounds
        if n_start_time > 0x00FFFFFF:
            logger.warning(f"entry_pulse_defn({n_entry}): "
                f"Start time 0x{n_start_time:06X} > 0x00FFFFFF")
        if n_start_time < PULSE_START_MIN and n_entry == 0:
            logger.warning(f"entry_pulse_defn({n_entry}): "
                f"Start time {n_start_time} < {PULSE_START_MIN}")
            logger.info(f"resetting to minimum {PULSE_START_MIN}")
            n_start_time = PULSE_START_MIN

        if n_wave_addr > 0x0FFF:
            logger.warning(f"entry_pulse_defn({n_entry}): "
                f"Wave addr 0x{n_wave_addr:04X} > 0x0FFF")

        if n_wave_len > 0x0FFF:
            logger.warning(f"entry_pulse_defn({n_entry}): "
                f"Wave len 0x{n_wave_len:04X} > 0x0FFF")

        if n_scale_gain > 0xFFFF:
            logger.warning(f"entry_pulse_defn({n_entry}): "
                f"Scale Gain 0x{n_scale_gain:04X} > 0xFFFF")

        if n_scale_addr > 0xFFFF:
            logger.warning(f"entry_pulse_defn({n_entry}): "
                f"Scale addr 0x{n_scale_addr:04X} > 0xFFFF")

        if n_flattop > 0x0001FFFF:
            logger.warning(f"entry_pulse_defn({n_entry}): "
                f"Flattop 0x{n_flattop:08X} > 0x0001FFFF")

        # Compute and write registers
        # 1) Write the Start Time
        n_wdata = n_start_time & 0x00FFFFFF
        n_waddr = 4 * 4 * n_entry  # offset calculation
        self.ser.write(str(n_wdata).encode('utf-8') + b'\xDD')
        self.ser.write(str(n_waddr).encode('utf-8') + b'\x8A')

        # 2) Write the Wave Length and Wave Address
        n_wdata = ((n_wave_len & 0x0FFF) << 16) | (n_wave_addr & 0x0FFF)
        n_waddr += 4
        self.ser.write(str(n_wdata).encode('utf-8') + b'\xDD')
        self.ser.write(str(n_waddr).encode('utf-8') + b'\x8A')

        # 3) Write the Scale Gain and Scale Address
        n_wdata = ((n_scale_gain & 0xFFFF) << 16) | (n_scale_addr & 0xFFFF)
        n_waddr += 4
        self.ser.write(str(n_wdata).encode('utf-8') + b'\xDD')
        self.ser.write(str(n_waddr).encode('utf-8') + b'\x8A')

        # 4) Write the Flattop
        n_wdata = n_flattop & 0x0001FFFF
        n_waddr += 4
        self.ser.write(str(n_wdata).encode('utf-8') + b'\xDD')
        self.ser.write(str(n_waddr).encode('utf-8') + b'\x8A')
        
