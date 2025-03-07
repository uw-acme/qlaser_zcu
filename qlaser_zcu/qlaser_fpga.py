import serial
import serial.tools.list_ports
import json
from .constants import *
from serial.serialutil import SerialException
from typing import TypedDict
from loguru import logger

class VersionsMismatchException(Exception):
    """Exception raised when versions do not match"""

class PulseConfig(TypedDict):
    """Pulse configuration
    """
    start_time: int  # start time of the pulse
    start_addr: int  # wavefrom table start address of the pulse
    wave_len: int  # size of the rise/fall
    scale_gain: float  # amplitude scaling factor
    scale_addr: float  # time step size
    sustain: int  # sustain time
    coefficents: list[int]  # polynomial coefficients

class QlaserFPGA:
    """Class to interact with the ZCU FPGA over serial port

        Args:
            portname (str, optional): Serial port to FPGA. Defaults to None to automatically select.
            baudrate (int, optional): Baudrate of the serial interface. Defaults to 115200.
            reset (bool, optional): Soft reset values in the FPGA into known states. Defaults to True.

        Raises:
            SerialException: No valid UART COM port found or given
        """
    def __init__(self, portname : str=None, baudrate: int=115200, reset=True):
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
        
        # check version
        self.vers = ", ".join(self.versions())
        if not (FPGA_VERSION in self.vers and FIRMWARE_VERSION in self.vers):
            self.logger.error(f"Version integrity check failed!\nExpected FPGA: {FPGA_VERSION}, Firmware: {FIRMWARE_VERSION}\nFound: {self.vers}")
            raise VersionsMismatchException((f"\n!!!Versions Mismatch! Please reload the bitsteam!!!\n!!!Incorrect version will result wrong bahavior!!!"))
        
        # Turn off command echo
        self.ser.write('0'.encode('utf-8') + CMD_ECHO)
        
        if reset:
            self.reset(flush_type="debug")
        
    
    def print_all(self, errors: str = "ignore", type="debug"):
        """Read and print all data from the serial port

        Args:
            errors (str, optional): How errors are handled when decoding the serial message. Defaults to "ignore".
            type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
        """
        while True:
            data = self.ser.readline()
            if not data:
                break
            msg = data.decode('utf-8', errors=errors).strip()
            if CMD_ERR_MSG in msg:
                self.logger.error(msg)
            else:
                eval(f"self.logger.{type}")(msg)

    def versions(self) -> list[str]:
        """Read and print all versions from the serial port

        Returns:
            list[str]: List of all versions
        """
        self.ser.write(CMD_VERSIONS)
        dumps = []
        data = self.ser.readlines()
        if not data:
            self.logger.error("No data received! Please make sure the device is powered on and running valid bitstream.")
        for i in data:
            dumps.append(i.decode('utf-8', errors="replace").strip())
        return dumps

    def reset(self, flush_type: str="debug"):
        """Soft reset data in the FPGA and reset pulse entry counter to 0
        
        Args:
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
        """
        self.ser.write(CMD_RESET)
        self.logger.debug("Sent soft reset command to FPGA")
        
        self.print_all(type=flush_type)  # Clear the buffer
        
        
    def xil_out32(self, addr: int, data: int, cmd: int) -> None:
        """Mimic Xil_Out32(addr, value) from the original C code. A generic write to FPGA function.

        Args:
            addr (int): Address to write to
            data (int): Data to write
            cmd (int): Write operation command, in hex format.
            
        Examples:
            Write 0x1234 to address 0x5678 in the pulse definition RAM (cmd = 0x8A)
            >>> xil_out32(0x5678, 0x1234, 0x8A)
        """
        self.ser.write(str(data).encode('utf-8') + CMD_SET_DATA)        
        # Then, send the address to the PD ram
        self.ser.write(str(addr).encode('utf-8') + bytes([cmd]))
        self.print_all(type="debug") # flush the buffer
    def __gpo_rd(self, format_spec="08x") -> str:
        """Read the general purpose output register
        
        Used (almost) internally only

        Args:
            format_spec (str, optional): String format to be output. Defaults to "08x".

        Returns:
            str: Value of the general purpose output register
        """
        self.print_all(type="debug")  # Clear the buffer
        self.ser.write(CMD_GPIO_RD)
        # This command is also used for real-time serial debug, with format of <some string message>: 0x<value>
        # Strip it to get the value
        data = self.ser.readline().decode('utf-8', errors="replace").strip().split("0x")
        return format(int(data[1], 16), format_spec)
    
    def read_regs(self) -> list[str]:
        """Read and print all registers

        Returns:
            list[str]: List of all register values
        """
        self.print_all(type="debug")  # clear the buffer
        self.ser.write(CMD_REG_DUMP)
        dumps = []
        for i in self.ser.readlines():
            dumps.append(i.decode('utf-8', errors="replace").strip())
        return dumps
    
    def read_errs(self) -> None:
        """Check channel errors. Print error message if any.
        """
        self.print_all(type="debug")  # clear the buffer
        self.ser.write(CMD_CH_ERR)
        erros = json.loads(self.ser.readline().decode('utf-8', errors="replace").strip())
        for k, v in erros.items():
            erro_type = k
            erro_chan = bin(v)[2:].zfill(C_MAX_CHANNELS)
    
            for j, char in enumerate(erro_chan):
                if char == '1':
                    logger.error(f"Found {erro_type} violation on channel {C_MAX_CHANNELS - j - 1}")
            else:
                logger.debug(f"No {erro_type} violations found on any channel")

    def pulse_trigger(self, flush_type: str = "debug", trigger_mode: str = "contiuous") -> None:
        """Tell FPGA to start the pulse sequence. Either triggering once or continuously.
        
        Args:
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
            trigger_mode (str, optional): Trigger mode. Either "contiuous" or "once". Defaults to "contiuous".
        """
        # raise error if trigger_mode is not valid
        if trigger_mode == "contiuous":
            self.ser.write(b't')
        elif trigger_mode == "once":
            self.ser.write(CMD_PULSE_TRIG)
        else:
            self.logger.error(f"Invalid trigger mode: {trigger_mode}. Valid options are 'contiuous' or 'once'")
            return
        self.logger.debug("Sent trigger command to FPGA")
        self.print_all(type=flush_type)

    def sel_pulse(self, seq_length: int, flush_type: str = "debug", channel: int | None = None) -> None:
        """Set the pulse sequence length

        Args:
            seq_length (int): Total duration of the pulse sequence
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
        """
        self.ser.write(f'{seq_length}'.encode('utf-8') + CMD_PULSE_SEQ)
        self.print_all(type=flush_type)

    def sel_channel(self, channel: int | None = None) -> None:
        """Select and enable channels

        Args:
            channel (int, optional): Channel to configure. Defaults to None to select all channels.
        """
        if channel is not None and (channel > C_MAX_CHANNELS or channel < 1):
            raise ValueError(f"Channel {channel} is out of range")
        if channel is None:
            channel = 99
        self.ser.write(f'{channel}'.encode('utf-8') + CMD_PULSE_CHSEL + CMD_PULSE_CHEN)
        
    def chan_sel(self, channel: int) -> None:
        """Select a channel to configure. Note on the physical hardware there are four PMOD DACs, with each has eight channels (channel A-H), totalling 32 channels.

        Args:
            channel (int): Channel to configure
        """
        if channel > C_MAX_CHANNELS or channel < 1:
            raise ValueError(f"Channel {channel} is out of range")
        self.ser.write(f'{channel}'.encode('utf-8') + CMD_PULSE_CHSEL)
        self.print_all(type="debug")  # flush out serial buffer
        
    def write_dc_chan(self, ch: int, value: int) -> None:
        """Write a value to DC channel

        Args:
            ch (int): Channel to write to. 32 total. Zero-indexed.
            value (int): Value to write for selected channel
        """
        if ch >= C_MAX_CHANNELS or ch < 0:
            self.logger.error(f"Channel {ch} is out of range. Set back to 0")
            ch = 0
        
        spi = int(ch / 8)
        dac_channel = int(ch % 8)

        # Format address
        addr = (spi << 3) + dac_channel
        
        self.ser.write(str(value).encode('utf-8') + CMD_SET_DATA)
        self.ser.write(str(addr).encode('utf-8') + CMD_DC_WR)
        
        self.print_all(type="debug")
        
        
    def write_wave_table(self, start_addr: int, values: list[int]) -> None:
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
        # If the length of the values is odd, write the last value
        if len(values) % 2:
            self.write_waves(start_addr + len(values) - 1, values[-1], 0)

    def write_waves(self, addr: int, val16_lo: int, val16_up: int) -> None:
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
        self.ser.write(str(val16_up * 2**C_BITS_ADDR_WAVE + val16_lo).encode('utf-8') + CMD_SET_DATA)
        self.ser.write(str(addr32).encode('utf-8') + CMD_WAVERAM_WR)
        
    def read_waves(self, addr: int) -> tuple[int, int]:
        """Read a chunk/pair of values from the wave table with a even-numbered start address

        Args:
            addr (int): Starting address of the wave table the data should be read from.
        
        Returns:
            tuple[int, int]: Two 16-bit values read from the wave table. First one is the bottom 16 bits, second one is the top 16 bits.
        """
        addr32 = addr // 2
        if bool(addr % 2):
            self.logger.warning(f"Address {addr} is not even. Values may not be read correctly!")
        self.ser.write(str(addr32).encode('utf-8') + CMD_WAVERAM_RD)
        data = self.ser.readline().decode('utf-8', errors="replace").strip()
        return int(data) & 0xFFFF, int(data) >> 16
    
    def read_wave_table(self, start_addr: int, length: int) -> list[int]:
        """Read a list of values from the wave table starting at the given even-numbered address.

        Args:
            start_addr (int): Starting address of the wave table
            length (int): Number of values to read
        
        Returns:
            list[int]: List of raw values read from the wave table
        """
        if start_addr < 0 or length < 0:
            self.logger.error("Start address and length must be positive!")
            return
        if start_addr + length >= C_LENGTH_WAVEFORM:
            self.logger.error(f"Start address + length must be less than {C_LENGTH_WAVEFORM}!")
            return
        if bool(start_addr % 2):
            self.logger.error("Start address must be even!")
            return
        values = []
        for i in range(start_addr, start_addr + length - 1, 2):
            bot, top = self.read_waves(i)
            values.append(bot)
            values.append(top)
        # If the length of the values is odd, read the last value
        if length % 2:
            values.append(self.read_waves(start_addr + length - 1)[0])
        return values

    def entry_pulse_defn(self,
                        n_entry: int,
                        n_start_time: int,  # minimum is 5
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
            n_start_time (int): Starting time of the pulse. There need to be at least 5 time units before each pulse starts.
            n_wave_addr (int): Starting address of the waveform table. Also known as "start address".
            n_wave_len (int): Duration of the rise of the pulse, unscaled.
            n_scale_gain (float): Amplitude scaling factor of the pulse. This value should always be any decimals between (0, 1]. Also known as "gain factor".
            n_scale_addr (float): Time scale factor of the pulse. This value should always be any decimals between [1, wave_len). Also known as "time step size" or "time factor".
            n_flattop (int): Sustain duration (whatever stays flat between rise and fall) of the pulse. Also known as "sustain"
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
        n_waddr = 4 * n_entry  # offset calculation
        self.ser.write(str(n_wdata).encode('utf-8') + CMD_SET_DATA)
        self.ser.write(str(n_waddr).encode('utf-8') + CMD_PDEFN_WR)

        # 2) Write the Wave Length and Wave Address
        n_wdata = ((n_wave_len & 0x0FFF) << 16) | (n_wave_addr & 0x0FFF)
        n_waddr += 1
        self.ser.write(str(n_wdata).encode('utf-8') + CMD_SET_DATA)
        self.ser.write(str(n_waddr).encode('utf-8') + CMD_PDEFN_WR)

        # 3) Write the Scale Gain and Scale Address
        n_wdata = ((n_scale_gain & 0xFFFF) << 16) | (n_scale_addr & 0xFFFF)
        n_waddr += 1
        self.ser.write(str(n_wdata).encode('utf-8') + CMD_SET_DATA)
        self.ser.write(str(n_waddr).encode('utf-8') + CMD_PDEFN_WR)

        # 4) Write the Flattop
        n_wdata = n_flattop & 0x0001FFFF
        n_waddr += 1
        self.ser.write(str(n_wdata).encode('utf-8') + CMD_SET_DATA)
        self.ser.write(str(n_waddr).encode('utf-8') + CMD_PDEFN_WR)
        
