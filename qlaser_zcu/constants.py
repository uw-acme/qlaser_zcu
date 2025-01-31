# Constants for the FPGA. Most of these are based on both firmware and hardware from BOOT.bin
UART_BAUD_DEFAULT = 115200
UART_DESCIP_KWD = "Interface 0"  # Keyword to search for UART interface

# Pulse Channel constants
C_BITS_ADC = 12
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
NUM_CHAN_DC   = 16
NUM_CHAN_AC   =  4

# Commands
CMD_REG_DUMP = b'P'  # Dump registers
CMD_ECHO = b'e'  # Echo command
CMD_RESET = b'\x52'  # Reset FPGA
CMD_GPIO_RD = b'r'  # Read GPIO value
CMD_GPIO_WR = b'o'  # Write GPIO value
CMD_PULSE_TRIG = b'\x80'  # Single trigger for AC pulse
CMD_PULSE_SEQ = b's'  # Sequence trigger for AC pulse
CMD_PULSE_CHEN = b'C'  # Enable pulse channel
CMD_PULSE_CHSEL = b'c'  # Select pulse channel
CMD_WAVERAM_WR = b'\x9A'  # Write to wave RAM
CMD_PDEFN_WR = b'\x8A'  # Write to pulse definition
CMD_WAVERAM_RD = b'\xBA'  # Read from wave RAM
CMD_PDEFN_RD = b'\xAA'  # Read from pulse definition
CMD_SET_DATA = b'\xDD'  # Set data to send
CMD_DC_WR = b'\x8D'  # Write to DC channel