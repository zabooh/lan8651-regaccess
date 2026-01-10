# LAN8651 Register Access Tools

A comprehensive toolset for direct access to the registers of the **Microchip LAN8651 10BASE-T1S MAC-PHY** chip via the OPEN Alliance TC6 Standard.

![LAN8651](https://img.shields.io/badge/Chip-LAN8651-blue)
![Platform](https://img.shields.io/badge/Platform-LAN966x-green)
![License](https://img.shields.io/badge/License-GPL--2.0-red)

## ⚠️ ARM Kernel Compatibility Issue

**The original `lan8651_debug.c` kernel module approach has a fundamental problem:**
- It tries to access private kernel structures that are not exported
- `struct lan865x_priv` and `struct oa_tc6` are internal to the driver
- This won't work with the ARM-compiled kernel

## 🔧 Better Solutions for ARM Systems

## 📋 Overview

The LAN8651 is a **10BASE-T1S MAC-PHY** chip that communicates with the host system via **SPI**. This toolset provides multiple approaches for register access:

- **Kernel driver extension** (recommended)
- **Debugfs interface** via existing kernel infrastructure
- **Ethtool integration** for network-based access
- **Direct register access** via TC6 protocol

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Tools    │    │  Kernel Module  │    │   Hardware      │
│                 │    │                 │    │                 │
│ lan8651_tool.py │◄──►│ lan8651_debug.c │◄──►│   LAN8651       │
│ lan8651_access  │    │      (cdev)     │    │   (SPI/TC6)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
  /dev/lan8651_debug      OA TC6 Framework         SPI Interface
```

## 📦 Components

### 1. **Kernel Module** (`lan8651_debug.c`)
- Character Device Interface (`/dev/lan8651_debug`)
- Integration with OA TC6 Framework
- Secure register access with validation
- Echo-Response verification

### 2. **C-Tool** (`lan8651_access.c`)
- Compact Command-Line Interface
- Predefined register names
- Cross-Platform Compilation (ARM/x86)
- Status decoding

### 3. **Python-Tool** (`lan8651_tool.py`)
- Extended user interface
- Bit-field analysis and decoding
- Automatic PHY detection
- Batch operations

## 🚀 Quick Start

### Installation

```bash
# Clone/download project
cd /home/martin/AIoT/lan9662/lan8651_regaccess

# Build all components
./build.sh

# Copy to target system
scp lan8651_debug.ko lan8651_access_arm lan8651_tool.py root@<target-ip>:~/
```

### First Steps

```bash
# 1. Load kernel module
sudo insmod lan8651_debug.ko

# 2. Check device
ls -la /dev/lan8651_debug

# 3. Test basic functions
./lan8651_tool.py status
./lan8651_access list
```

## 📖 Usage

### Reading registers

```bash
# With register names
./lan8651_access read MAC_NET_CTL
./lan8651_tool.py read TC6_STATUS0

# With hex address
echo "read 0x10000" > /dev/lan8651_debug
cat /dev/lan8651_debug

# With decoding
./lan8651_tool.py read MAC_NET_CTL  # Shows bit meanings
```

### Writing registers

```bash
# Enable MAC TX/RX
./lan8651_access write MAC_NET_CTL 0x0C
./lan8651_tool.py enable

# Direct via device
echo "write 0x10000 0x0C" > /dev/lan8651_debug
```

### Status monitoring

```bash
# Complete status display
./lan8651_tool.py status

# Specific areas
./lan8651_access status
./lan8651_tool.py phy-id
```

## 🗂️ Register Reference

### MAC Register

| Register | Address | Bits | Description |
|----------|---------|------|--------------|
| `MAC_NET_CTL` | 0x00010000 | [3:2] | Network Control (TXEN, RXEN) |
| `MAC_NET_CFG` | 0x00010001 | [7:4] | Network Config (Promiscuous, Multicast) |
| `MAC_L_SADDR1` | 0x00010022 | [31:0] | MAC Address Low (Bytes 0-3) |
| `MAC_H_SADDR1` | 0x00010023 | [15:0] | MAC Address High (Bytes 4-5) |
| `MAC_L_HASH` | 0x00010020 | [31:0] | Hash Table Low |
| `MAC_H_HASH` | 0x00010021 | [31:0] | Hash Table High |

### TC6 Control Register

| Register | Address | Bits | Description |
|----------|---------|------|--------------|
| `TC6_STDCAP` | 0x0002 | [8] | Standard Capabilities |
| `TC6_RESET` | 0x0003 | [0] | Software Reset |
| `TC6_CONFIG0` | 0x0004 | [15,12] | SYNC, ZARFE Enable |
| `TC6_STATUS0` | 0x0008 | [6:0] | Status Flags |
| `TC6_BUFFER_STATUS` | 0x000B | [15:8,7:0] | TX Credits, RX Chunks |
| `TC6_INT_MASK0` | 0x000C | [5:0] | Interrupt Masks |

### PHY Register (via TC6)

| Register | Address | Standard | Description |
|----------|---------|----------|--------------|
| `PHY_BMCR` | 0xFF00 | IEEE 802.3 | Basic Mode Control |
| `PHY_BMSR` | 0xFF01 | IEEE 802.3 | Basic Mode Status |
| `PHY_ID1` | 0xFF02 | IEEE 802.3 | PHY Identifier 1 |
| `PHY_ID2` | 0xFF03 | IEEE 802.3 | PHY Identifier 2 |
| `PHY_ANAR` | 0xFF04 | IEEE 802.3 | Auto-Negotiation Advertisement |

## 🔧 Bit Field Definitions

### MAC_NET_CTL (0x00010000)
```
Bit 3: TXEN    - Transmit Enable (1=Enable, 0=Disable)
Bit 2: RXEN    - Receive Enable (1=Enable, 0=Disable)
```

### TC6_STATUS0 (0x0008)
```
Bit 6: RESETC              - Reset Complete
Bit 5: HEADER_ERROR        - Header Error
Bit 4: LOSS_OF_FRAME_ERROR - Loss of Frame Error  
Bit 3: RX_BUFFER_OVERFLOW  - RX Buffer Overflow
Bit 0: TX_PROTOCOL_ERROR   - TX Protocol Error
```

### TC6_BUFFER_STATUS (0x000B)
```
Bits 15:8: TX_CREDITS_AVAILABLE  - Available TX Credits (0-255)
Bits  7:0: RX_CHUNKS_AVAILABLE   - Available RX Chunks (0-255)
```

## 📊 Example Workflows

### 1. MAC-PHY Initialization

```bash
#!/bin/bash
# MAC-PHY Setup Script

echo "=== LAN8651 Initialization ==="

# 1. Check reset status
echo "Checking reset status..."
./lan8651_tool.py read TC6_STATUS0

# 2. Read capabilities
echo "Reading capabilities..."
./lan8651_access read TC6_STDCAP

# 3. Configure MAC
echo "Configuring MAC..."
./lan8651_access write MAC_NET_CFG 0x00    # Clear config
./lan8651_access write MAC_NET_CTL 0x0C    # Enable TX+RX

# 4. Check status
echo "Final status:"
./lan8651_tool.py status
```

### 2. Diagnostic Script

```bash
#!/bin/bash
# LAN8651 Diagnostic Script

echo "=== LAN8651 Diagnostics ==="

# PHY Identification
echo "1. PHY Identification:"
./lan8651_tool.py phy-id

# Link Status
echo "2. Link Status:"
./lan8651_access read PHY_BMSR

# Error Status
echo "3. Error Status:"
./lan8651_tool.py read TC6_STATUS0

# Buffer Status
echo "4. Buffer Status:"
./lan8651_access read TC6_BUFFER_STATUS

# MAC Status
echo "5. MAC Status:"
./lan8651_access read MAC_NET_CTL
```

### 3. Performance-Monitoring

```python
#!/usr/bin/env python3
# Performance Monitor

import time
import subprocess

def read_register(reg):
    result = subprocess.run(['./lan8651_access', 'read', reg], 
                          capture_output=True, text=True)
    if "0x" in result.stdout:
        return int(result.stdout.split("0x")[2].split()[0], 16)
    return 0

print("LAN8651 Performance Monitor")
print("Press Ctrl+C to stop")

try:
    while True:
        # Read buffer status
        buffer_status = read_register('TC6_BUFFER_STATUS')
        tx_credits = (buffer_status >> 8) & 0xFF
        rx_chunks = buffer_status & 0xFF
        
        # Display status
        timestamp = time.strftime("%H:%M:%S")
        print(f"{timestamp}: TX Credits: {tx_credits:3d}, RX Chunks: {rx_chunks:3d}")
        
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\nMonitoring stopped.")
```

## 🐛 Debugging & Troubleshooting

### Common Problems

#### "Device not found"
```bash
# Check and solution
lsmod | grep lan8651_debug      # Module loaded?
sudo insmod lan8651_debug.ko    # If not, load it
dmesg | tail                    # Check kernel log
```

#### "LAN8651 device not found"  
```bash
# Check LAN865x driver
lsmod | grep lan865x
ip link show                    # Check interfaces
cat /proc/net/dev              # Network devices
```

#### Register access failed
```bash
# Check TC6 status
./lan8651_tool.py read TC6_STATUS0

# Test SPI connection
./lan8651_access read TC6_STDCAP

# Reset if necessary
echo "write 0x3 0x1" > /dev/lan8651_debug  # Software Reset
```

### Enable Debug Output

```bash
# Enable kernel debug
echo 8 > /proc/sys/kernel/printk

# Load module with debug
modprobe lan8651_debug debug=1

# SPI debug (if available)
echo 1 > /sys/module/spi_core/parameters/debug
```

## 🔒 Security Notes

- **Root privileges required** for kernel module
- **Direct hardware access** may affect system  
- **Backup register values** before modifications
- **Use reset functionality** for critical errors

## 🧪 Testing

### Unit Tests

```bash
# Test basic functionality
./test/basic_tests.sh

# Check register consistency
./test/register_tests.sh

# Performance test
./test/performance_tests.sh
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: LAN8651 Tools Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Install Cross Compiler
      run: sudo apt-get install gcc-arm-linux-gnueabihf
    - name: Build Tools
      run: ./build.sh
    - name: Run Tests
      run: ./test/run_all_tests.sh
```

## 📚 Further Documentation

- [OPEN Alliance TC6 Specification v1.1](https://opensig.org/download/document/OPEN_Alliance_10BASET1x_MAC-PHY_Serial_Interface_V1.1.pdf)
- [LAN8651 Datasheet](https://www.microchip.com/wwwproducts/en/LAN8651)
- [Linux OA TC6 Framework](https://www.kernel.org/doc/html/latest/networking/oa_tc6.html)
- [10BASE-T1S Standard IEEE 802.3cg](https://standards.ieee.org/standard/802_3cg-2019.html)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push branch (`git push origin feature/amazing-feature`)
5. Create Pull Request

## 📄 License

This project is licensed under the **GPL-2.0+ License** - see [LICENSE](LICENSE) for details.

## 👥 Authors

- **Martin** - Initial work
- **Microchip Technology** - LAN8651 Hardware and drivers

## 🙏 Acknowledgments

- OPEN Alliance for TC6 Standard
- Linux Kernel Community for OA TC6 Framework
- Microchip for hardware documentation

---

**⚠️ Note:** This tool is intended for development and debugging purposes. Do not use it in production environments without proper testing.