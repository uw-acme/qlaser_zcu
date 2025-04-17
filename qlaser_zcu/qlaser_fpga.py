import serial
import serial.tools.list_ports
import json
from .constants import *  # noqa: F403
from serial.serialutil import SerialException
from typing import TypedDict
from loguru import logger

class VersionsMismatchException(Exception):
    """Exception raised when versions do not match"""

class PulseConfig(TypedDict):
    """Pulse configuration, a typed dictionary to store pulse parameters
    
    Attributes:
        wave_id (int): Wave ID of the waveform. Can be calculated by wave_id = start_address + wave_length * 2^16
        start_time (int): Start time of the pulse. Minimum is 5.
        scale_gain (float): Amplitude scaling factor
        scale_addr (float): Time step size
        sustain (int): Sustain time
    """
    wave_id:    int    # ID of the waveform. Can be calculated by wave_id = start_address + wave_length * 2^16
    start_time: int    # start time of the pulse
    scale_gain: float  # amplitude scaling factor
    scale_addr: float  # time step size
    sustain:    int    # sustain time

class QlaserFPGA:
    """Core Class to interact with the ZCU FPGA over serial port

        Args:
            portname (str, optional): Serial port to FPGA. Defaults to None to automatically select.
            baudrate (int, optional): Baudrate of the serial interface. Defaults to 115200.

        Raises:
            SerialException: No valid UART COM port found or given
        """
    def __init__(self, portname : str=None, baudrate: int=UART_BAUD_DEFAULT):
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
            if not self.vers:
                raise SerialException("No valid firmware found on FPGA or FPGA is not powered on!")
            else:
                raise VersionsMismatchException((f"\n!!!Versions Mismatch! Please reload the bitsteam!!!\n!!!Incorrect version will result wrong bahavior!!!"))
        
        # Turn off command echo
        self.ser.write('0'.encode('utf-8') + CMD_ECHO)
        
    
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
        
        
    def xil_out32(self, addr: int, data: int, cmd: int | bytes) -> None:
        """Mimic Xil_Out32(addr, value) from the original C code but for specific block. 
        A generic write to a FPGA's memory location by writing 32-bit data and 16-bit address with a block-specific command.

        Args:
            addr (int): Address to write to
            data (int): Data to write
            cmd (int): Write operation command, in hex format. This specifies the block to write to.
            
        Examples:
            Write 0x1234 to address 0x5678 in the pulse definition RAM (cmd = 0x8A)
            >>> xil_out32(0x5678, 0x1234, 0x8A)
        """

        if isinstance(cmd, int):
            cmd = bytes([cmd])
            
        self.ser.write(str(((addr & 0xFFFF) << 32) | (data & 0xFFFFFFFF)).encode('utf-8') + cmd)
        
    def xil_in32(self, addr: int, cmd: int | bytes) -> int:
        """Mimic Xil_In32(addr) from the original C code but for specific block. 
        A generic read from a a FPGA's memory location by writing 16-bit address with a block-specific command and reading 32-bit data.
        
        Args:
            addr (int): Address to read from
            cmd (int): Read operation command, in hex format. This specifies the block to read from.
        
        Returns:
            int: Data read from the address
        """
        
        if type(cmd) == int:
            cmd = bytes([cmd])
        # flush out any existing data in the buffer
        self.print_all(type="debug")
        self.ser.write(str(addr).encode('utf-8') + cmd)
        data = self.ser.readline().decode('utf-8', errors="replace").strip()
        return int(data)
    
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
        cnt_err = 0
        for k, v in erros.items():
            erro_type = k
            erro_chan = bin(v)[2:].zfill(C_MAX_CHANNELS)
    
            for j, char in enumerate(erro_chan):
                if char == '1':
                    logger.error(f"Found {erro_type} violation on channel {C_MAX_CHANNELS - j - 1}")
                    cnt_err += 1
        if cnt_err == 0:
            logger.info("No channel errors found")
        else:
            logger.error(f"Found {cnt_err} channel errors")

    def pulse_trigger(self, flush_type: str = "debug", trigger_mode: str = "contiuous") -> None:
        """**DEPRECATED** Tell FPGA to start the pulse sequence. Either triggering once or continuously.
        
        Args:
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
            trigger_mode (str, optional): Trigger mode. Either "contiuous" or "once". Defaults to "contiuous".
        """
        self.ser.write(CMD_PULSE_TRIG)
        self.logger.debug("Sent trigger command to FPGA")
        self.print_all(type=flush_type)

    def set_seq(self, seq_length: int, flush_type: str = "debug", channel: int | None = None) -> None:
        """Set the pulse sequence length

        Args:
            seq_length (int): Total duration of the pulse sequence
            flush_type (str, optional): Type of log message. Either "info" or "debug". Defaults to "debug".
        """
        self.ser.write(f'{seq_length}'.encode('utf-8') + CMD_PULSE_SEQ)
        self.print_all(type=flush_type)
        
    def read_en(self) -> list[int]:
        """Read enabled channels

        Returns:
            list[int]: Enabled channels as a bitmask
        """
        self.print_all(type="debug")  # clear the buffer
        self.ser.write(CMD_REG_DUMP)
        data = self.ser.readlines()
        
        for i in data:
            if "ADR_PULSE_REG_CHEN" in str(i):
                enabled = i.decode("utf-8").split("0x")[-1].strip()
                break
        else:
            logger.error("No ADR_PULSE_REG_CHEN register found in the response.")
            return
            
        converted = bin(int(enabled, 16))[2:].zfill(32)[::-1]  # reverse the string to match channel order        
        return [i for i, x in enumerate(converted) if x == "1"]
        
        
    def chan_en(self, channels: int | list[int]) -> None:
        """Enable one or multiple channels to be configured (0-31).

        Args:
            channels (int | list[int]): Channel(s) to enable. 
        """
        if isinstance(channels, int):
            channels = [channels]
            
        data = 0
        for i in channels:
            if i > C_MAX_CHANNELS or i < 0:
                logger.warning(f"Ignored invalid channel {i}.")
            else:
                data |= 1 << i
                
        if data == 0:
            logger.error("No Valid channels selected!")
            return
            
        self.ser.write(f'{data}'.encode('utf-8') + CMD_PULSE_CHEN)
        self.print_all(type="debug")
        
    def chan_sel(self, channel: int) -> None:
        """Select a single channel (0-31) to configure.

        Args:
            channel (int): Channel to configure
        """
        if channel > C_MAX_CHANNELS or channel < 0:
            self.logger.error(f"Channel {channel} is out of range. Set back to 0")
            channel = 0
        self.ser.write(f'{1 << channel}'.encode('utf-8') + CMD_PULSE_CHSEL)
        self.print_all(type="debug")  # flush out serial buffer
        
    def write_dc_chan(self, ch: int, value: int) -> None:
        """Write a value to DC channel

        Args:
            ch (int): Channel (0-31) to write to. 32 total. Zero-indexed.
            value (int): Value to write for selected channel
        """
        if ch >= C_MAX_CHANNELS or ch < 0:
            self.logger.error(f"Channel {ch} is out of range. Set back to 0")
            ch = 0
        
        spi = int(ch / 8)
        dac_channel = int(ch % 8)

        # Format address
        addr = (spi << 3) + dac_channel
        
        self.xil_out32(addr, value, CMD_DC_WR)
        
        self.print_all(type="debug")
        
    def read_waves(self, addr: int) -> tuple[int, int]:
        """Read a pair of values from the wave table with a even-numbered start address

        Args:
            addr (int): Starting address of the wave table the data should be read from.
        
        Returns:
            tuple[int, int]: Two 16-bit values read from the wave table. First one is the bottom 16 bits, second one is the top 16 bits.
        """
        addr32 = addr // 2
        if bool(addr % 2):
            self.logger.warning(f"Address {addr} is not even. Values may not be read correctly!")
        data = self.xil_in32(addr32, CMD_WAVERAM_RD)
        return int(data) & 0xFFFF, int(data) >> 16
    
    def read_wave_table(self, start_addr: int = 0, length: int = C_LENGTH_WAVEFORM) -> list[int]:
        """Read a list of values from the wave table starting at the given address.

        Args:
            start_addr (int, optional): Starting address of the wave table. Defaults to 0.
            length (int, optional): Number of values to read. Defaults to C_LENGTH_WAVEFORM.
        
        Returns:
            list[int]: List of raw values read from the wave table, None on error.
        """
        if start_addr < 0 or length < 0:
            self.logger.error("Start address and length must be positive!")
            return
        if start_addr + length > C_LENGTH_WAVEFORM:
            self.logger.error(f"Start address + length must be less than {C_LENGTH_WAVEFORM}!")
            return
        
        end_addr = start_addr + length

        self.print_all(type="debug")  # flush out serial buffer
        self.ser.write(f'{(start_addr << 16) + end_addr}'.encode('utf-8') + CMD_RD_WAVE)
        data = self.ser.readline().decode('utf-8', errors="replace").strip().split(",")
            
        values = []
        for i in data:
            if i.isdigit():
                values.append(int(i))
        
        return values
        
    def read_pulse_defn(self, n_entry: int = C_NUM_WAVEFORM, start: int = 0) -> list[PulseConfig]:
        """Read pulse definition from the FPGA. This is a list of pulse configurations.

        Args:
            n_entry (int, optional): Number of entries to read. Defaults to C_NUM_WAVEFORM - 1, which is maximum numbers of paramters can be stored.
            start (int, optional): Starting entry. Defaults to 0.

        Returns:
            list[PulseConfig]: List of pulse configurations
        """
        self.print_all(type="debug")
        if n_entry > C_NUM_WAVEFORM or n_entry <= 0:
            self.logger.error(f"Entry {n_entry} is out of range. Set back to default")
            n_entry = C_NUM_WAVEFORM
        if start > C_NUM_WAVEFORM or start < 0:
            self.logger.error(f"Start {start} is out of range. Set back to default")
            start = 0
        if start + n_entry > C_NUM_WAVEFORM:
            self.logger.error(f"Start + Entry {start + n_entry} is out of range. Set back to defaults")
            start = 0
            n_entry = C_NUM_WAVEFORM
            
        self.ser.write(f'{((4*(start)) << 16)+4*(n_entry)}'.encode('utf-8') + CMD_RD_PDEFN)
        values = self.ser.readline().decode('utf-8', errors="replace").strip().split(",")
        
        configs = []
        
        # read values in a group of 4
        for i in range(start, len(values), 4):
            if all(values[i+j].isdigit() for j in range(4)):
                start_time = int(values[i]) & 0x00FFFFFF
                scale_gain = ((int(values[i+2]) >> 16) & 0xFFFF) / 2**BIT_FRAC_GAIN
                scale_addr = (int(values[i+2]) & 0xFFFF) / 2**BIT_FRAC
                sustain = int(values[i+3]) & 0x0001FFFF

                configs.append(PulseConfig(
                    wave_id=int(values[i+1]),
                    start_time=start_time,
                    scale_gain=scale_gain,
                    scale_addr=scale_addr,
                    sustain=sustain
                ))
            
        return configs
        
    def write_wave_table(self, start_addr: int, values: list[int], all_chan: bool = False) -> int:
        """Write a list of values pairs to the wave table starting at the given even-numbered address.

        Args:
            start_addr (int): Starting address of the wave table
            values (list[int]): List of values to be written
            all_chan (bool, optional): Write to all channels. Note this will change the channel select and need to call `chan_sel` again  Defaults to False.
            
        Returns:
            int: Wave ID of the waveform written to the wave table.
        """
        if bool(start_addr % 2):
            self.logger.error("Start address must be even!")
            return
        if all_chan:
            self.logger.debug("Writing same waveforms to all channels.")
            self.ser.write('99'.encode('utf-8') + CMD_PULSE_CHSEL)
        for i in range(start_addr, start_addr + len(values) - 1, 2):
            self.write_waves(i, values[i-start_addr], values[i-start_addr+1])
        # If the length of the values is odd, write the last value
        if len(values) % 2:
            self.write_waves(start_addr + len(values) - 1, values[-1], 0)
        return (len(values) << 16) + (start_addr & 0x0FFF)

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

        self.xil_out32(addr32, val16_up * 2**C_BITS_ADDR_WAVE + val16_lo, CMD_WAVERAM_WR)

    def entry_pulse_defn(self,
                        n_wave: int,
                        n_start_time: int,  # minimum is 5
                        n_scale_gain: float,
                        n_scale_addr: float,
                        n_flattop: int,
                        n_entry: int | None = None) -> None:
        """Write pulse parameters to the FPGA.
        Prints warnings if parameters exceed certain limits and
        Whenever this function gets called, a entry pointer increments by 1.

        Args:
            n_wave (int): Wave ID of the waveform. Can be calculated by wave_id = start_address + wave_length * 2^16
            n_start_time (int): Start time of the pulse. Minimum is 5.
            n_scale_gain (float): Amplitude scaling factor
            n_scale_addr (float): Time step size
            n_flattop (int): Sustain time
            n_entry (int | None, optional): Nth pulse entry. This value should and only be incremented by 1 every time this function is called. Defaults to None to auto allocate the next entry. Note that the automatic allocation will be slower than manually setting the entry, but it is more convenient.
        """
        
        if n_entry is None:
            pdefs = self.read_pulse_defn()
            for i in pdefs:
                if sum(list(i.values())) == 0:
                    n_entry = pdefs.index(i)
                    self.logger.debug(f"Found empty entry {n_entry} in pulse definition.")
                    break
            else:
                logger.warning("No empty entry found. Loop back and overwrite the first entry.")
                n_entry = 0
        
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
        self.xil_out32(n_waddr, n_wdata, CMD_PDEFN_WR)

        # 2) Write the Wave Length and Wave Address (basically the wave ID)
        n_wdata = n_wave
        n_waddr += 1
        self.xil_out32(n_waddr, n_wdata, CMD_PDEFN_WR)

        # 3) Write the Scale Gain and Scale Address
        n_wdata = ((n_scale_gain & 0xFFFF) << 16) | (n_scale_addr & 0xFFFF)
        n_waddr += 1
        self.xil_out32(n_waddr, n_wdata, CMD_PDEFN_WR)

        # 4) Write the Flattop
        n_wdata = n_flattop & 0x0001FFFF
        n_waddr += 1
        self.xil_out32(n_waddr, n_wdata, CMD_PDEFN_WR)
        
    def clear_ram_defn(self) -> None:
        """Clear all pulse definitions in the FPGA
        """
        for i in range(C_NUM_WAVEFORM * 4):
            self.xil_out32(i, 0, CMD_PDEFN_WR)
        self.print_all(type="debug")  # flush out serial buffer
        
    def clear_wave_table(self) -> None:
        """Clear all waveforms in the FPGA
        """
        for i in range(0, C_LENGTH_WAVEFORM, 2):
            self.write_waves(i, 0, 0)
        self.print_all(type="debug")
            
    
        
