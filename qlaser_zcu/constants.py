# Constants for the FPGA. Most of these are based on both firmware and hardware from BOOT.bin
UART_BAUD_DEFAULT = 115200
UART_DESCIP_KWD = "Interface 0"  # Keyword to search for UART interface

FPGA_VERSION = "3AC10001"  #FPGA version
FIRMWARE_VERSION = "1.0.j"  # Firmware version

# DC constants
VREF_INTERNAL = "internal"
VREF_EXTERNAL = "external"
VREF_TYPE     = VREF_INTERNAL   # or 'external'
VOLTAGE_REF   = 1.25

# UART message format. Should be 0xAAAADDDDDDDD + command format
FMT_ADDR_START = 32  # starting bit for address

# Pulse Channel constants
C_LENGTH_WAVEFORM = 4096  # Number of output data values from waveform RAM (4kx16-bit)
C_BITS_ADDR_WAVE = 16
C_BITS_GAIN_FACTOR = 16
C_BITS_TIME_FACTOR = 16
C_MAX_CHANNELS = 32
C_ERR_BITS = 8
BIT_FRAC = 8
BIT_FRAC_GAIN = C_BITS_GAIN_FACTOR - 1
PULSE_START_MIN = 5  # Minimum start time for pulse

VREF_INTERNAL = "internal"
VREF_EXTERNAL = "external"
VREF_TYPE     = VREF_INTERNAL   # or 'external'
VOLTAGE_REF   = 1.25
#VOLTAGE_REF   = 3.3

# Configuration
DAC_BITS_RES  = 12
FMC_BITS_RES  = 16
NUM_CHAN_DC   = 16
NUM_CHAN_AC   =  4

# Commands
# Legacy ASCII Commands
CMD_VERSIONS = b'v'  # Get versions
CMD_REG_DUMP = b'P'  # Dump registers
CMD_ECHO = b'e'  # Echo command
CMD_RESET = b'\x52'  # Reset FPGA
CMD_GPIO_RD = b'r'  # Read GPIO value
CMD_GPIO_WR = b'o'  # Write GPIO value
CMD_PULSE_SEQ = b's'  # Sequence trigger for AC pulse
CMD_PULSE_CHEN = b'C'  # Enable pulse channel
CMD_PULSE_CHSEL = b'c'  # Select pulse channel
CMD_PD_READ = b'W'  # Read back from pulse definition

# Binary Commands specificatlly designed of this package
CMD_PULSE_TRIG = b'\x80'  # Single trigger for AC pulse

CMD_WAVERAM_WR = b'\x9A'  # Write to wave RAM
CMD_PDEFN_WR = b'\x8A'  # Write to pulse definition. Should also be the base addr of pulse channel
CMD_DC_WR = b'\x8D'  # Write to DC channel
CMD_MISC_WR = b'\x8B'  # Write to misc register

CMD_PDEFN_RD = b'\xAA'  # Read from pulse definition
CMD_WAVERAM_RD = b'\xAB'  # Read from wave RAM
CMD_AC_RD = b'\xAC'  # Read from AC channels. Including selected pulse channel RAM and the register value from CC-P
CMD_DC_RD = b'\xDC'  # Read from DC channels
CMD_MISC_RD = b'\xBC'  # Read from misc register

CMD_CH_ERR = b'\xAE'  # Get channel errors

# Other constants
CMD_ERR_MSG = "*E"  # Error message from firmware