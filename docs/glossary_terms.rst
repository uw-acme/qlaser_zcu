Glossary Terms
###################

.. glossary::

  FPGA
    Field Programmable Gate Array. An integrated circuit that can be configured by a customer or a designer after manufacturing.   
  
  register
    A small amount of storage space within a computer's processor that is used to store data temporarily. Registers are used to hold data that is being processed by the processor.

  RAM
    Random Access Memory. A type of computer memory that provides storage space within the FPGA. RAM allows data to be read from or written to any memory location. In this project, RAM is used to store the parameters of the waveforms and the base values of the waveforms.

  address
    A unique identifier for a memory location in a computer's memory. Addresses are used to access data stored in memory.

  digital
    A type of signal that is discrete and binary, meaning it can only have two values: 0 or 1. Digital signals are used in many applications, such as computers, telecommunication systems, and control systems.

  analog
    A type of signal that is continuous and can have any value within a range. Analog signals are used in many applications, such as audio and video systems, sensors, and control systems.

  channels
    A path for transmitting data between devices. For the hardware in this project, a channel is used to generate laser control signals for manipulating trapped ions.

  DAC
    Digital-to-Analog Converter. A device that converts digital signals to analog signals.

  PMOD
    A small I/O module that can be plugged into a PMOD connector on a FPGA board. PMOD modules are used to add additional functionality to a FPGA board, such as digital-to-analog conversion and communication interfaces in this project.

  SPI
    Serial Peripheral Interface. A synchronous serial communication interface that is used to communicate between the FPGA and external DACs.

  bitstream
    A file that contains the configuration data for an FPGA. The bitstream is loaded into the FPGA to configure it.

  bit
    A binary digit, which can have a value of 0 or 1. Bits are the basic unit of information in computing and digital communications.

  byte
    A unit of digital information that consists of 8 bits. Bytes are used to represent characters, numbers, and other data in computing.

  word
    A unit of digital information that is the natural size of data handled by a computer's processor. The size of a word depends on the architecture of the processor. For this project, a word is 32-:term:`bit`.

  instructions
    A set of commands that FPGA hardware can execute. Instructions are used to perform operations on data, such as arithmetic and logical operations in the hardware.

  entry
    A single waveform parameters in the pulse definition RAM. Each entry is accumulative in the pulse definition RAM.
  
  start time
    Starting time of the pulse. There need to be at least 5 time units before each pulse starts.

  start address
    The address or location in the waveform table RAM where the base value of the rise of the waveform is stored.

  wave length
    Duration of the rise of the pulse.

  gain factor
    Amplitude scaling factor of the pulse. This value should always be any decimals between (0, 1].

  time factor
    Step size of the pulse. Defines how much the address of the wavefrom table should be increment/decrement. This value should always be any decimals between [1, wave_len).

  sustain
    Sustain duration (whatever stays flat between rise and fall) of the pulse. 