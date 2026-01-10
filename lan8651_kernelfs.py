#!/usr/bin/env python3
"""
LAN8651 Register Access via existing kernel debugfs/sysfs interfaces

This approach uses existing kernel infrastructure instead of 
creating a custom kernel module.
"""

import os
import glob
import struct
import subprocess
import sys

class LAN8651Debugfs:
    def __init__(self):
        self.debugfs_path = None
        self.sysfs_path = None
        self.find_interfaces()
    
    def find_interfaces(self):
        """Find LAN8651 network interfaces via sysfs"""
        
        # Look for network interfaces using lan865x driver
        net_devices = glob.glob("/sys/class/net/*/device/driver")
        
        for device_path in net_devices:
            try:
                # Read the driver name
                driver_link = os.readlink(device_path)
                if "lan865x" in driver_link:
                    # Found a LAN8651 interface
                    iface_name = device_path.split('/')[-3]
                    self.sysfs_path = f"/sys/class/net/{iface_name}/device"
                    print(f"Found LAN8651 interface: {iface_name}")
                    break
            except OSError:
                continue
        
        # Look for debugfs entries
        if os.path.exists("/sys/kernel/debug"):
            # Check for TC6 or lan865x specific debug entries
            debug_paths = [
                "/sys/kernel/debug/tc6",
                "/sys/kernel/debug/lan865x",
                "/sys/kernel/debug/spi"
            ]
            
            for path in debug_paths:
                if os.path.exists(path):
                    self.debugfs_path = path
                    print(f"Found debug interface: {path}")
                    break
    
    def read_via_debugfs(self, address):
        """Try to read register via debugfs if available"""
        
        if not self.debugfs_path:
            return None
        
        # This would depend on what the kernel driver exposes
        reg_file = f"{self.debugfs_path}/registers"
        if os.path.exists(reg_file):
            try:
                with open(reg_file, 'w') as f:
                    f.write(f"0x{address:08x}")
                
                with open(reg_file, 'r') as f:
                    result = f.read().strip()
                    return int(result, 0)
            except Exception as e:
                print(f"Debugfs read error: {e}")
        
        return None
    
    def read_via_spi_debug(self, address):
        """Try to access SPI debug information"""
        
        if not self.sysfs_path:
            return None
        
        # Check if there are SPI device attributes we can use
        spi_attrs = glob.glob(f"{self.sysfs_path}/spi*/registers") 
        if spi_attrs:
            try:
                with open(spi_attrs[0], 'w') as f:
                    f.write(f"read 0x{address:08x}")
                
                with open(spi_attrs[0], 'r') as f:
                    result = f.read().strip()
                    # Parse result - format depends on kernel implementation
                    if "=" in result:
                        value_str = result.split("=")[1].strip()
                        return int(value_str, 0)
            except Exception as e:
                print(f"SPI debug read error: {e}")
        
        return None
    
    def read_via_ethtool(self, iface, address):
        """Try to read via ethtool register dump"""
        
        try:
            # Use ethtool to dump registers
            result = subprocess.run(['ethtool', '-d', iface], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse ethtool output for our register
                lines = result.stdout.split('\n')
                for line in lines:
                    if f"0x{address:08x}" in line.lower():
                        # Extract value from line
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if f"0x{address:08x}" in part.lower() and i+1 < len(parts):
                                return int(parts[i+1], 0)
        except Exception as e:
            print(f"Ethtool error: {e}")
        
        return None
    
    def read_register(self, address):
        """Try multiple methods to read register"""
        
        print(f"Attempting to read register 0x{address:08x}")
        
        # Method 1: debugfs
        value = self.read_via_debugfs(address)
        if value is not None:
            print(f"Read via debugfs: 0x{value:08x}")
            return value
        
        # Method 2: SPI debug
        value = self.read_via_spi_debug(address)
        if value is not None:
            print(f"Read via SPI debug: 0x{value:08x}")
            return value
        
        # Method 3: Find network interface and try ethtool
        if self.sysfs_path:
            iface = self.sysfs_path.split('/')[-2]
            value = self.read_via_ethtool(iface, address)
            if value is not None:
                print(f"Read via ethtool: 0x{value:08x}")
                return value
        
        print("All read methods failed - kernel driver extension needed")
        return None

def show_register_info(address, value):
    """Show detailed register information"""
    
    print(f"\nRegister 0x{address:08x} = 0x{value:08x} ({value})")
    print(f"Binary: {value:032b}")
    
    # Show known LAN8651 registers
    reg_names = {
        0x10000: "ID_REV",
        0x10001: "STATUS0", 
        0x10002: "STATUS1",
        0x10003: "CONFIG0",
        0x10004: "CONFIG1",
        0x10005: "CONFIG2",
        0x10006: "CONFIG3",
        0x10007: "CONFIG4",
        0x10020: "FIFO_SIZE",
        0x10021: "CHUNK_SIZE"
    }
    
    if address in reg_names:
        print(f"Name: {reg_names[address]}")
        
        # Decode specific registers
        if address == 0x10000:  # ID_REV
            chip_id = (value >> 16) & 0xFFFF
            rev_id = value & 0xFFFF
            print(f"Chip ID: 0x{chip_id:04x}, Revision: 0x{rev_id:04x}")
        
        elif address == 0x10001:  # STATUS0
            print(f"TX_FRAME_CHECK_SEQUENCE_ERROR: {(value >> 0) & 1}")
            print(f"TX_FRAME_ERROR: {(value >> 1) & 1}")
            print(f"TX_BUFFER_OVERFLOW_ERROR: {(value >> 2) & 1}")
            print(f"TX_FIFO_UNDERFLOW: {(value >> 3) & 1}")
            print(f"RX_FIFO_OVERFLOW: {(value >> 4) & 1}")
            print(f"RX_HEADER_ERROR: {(value >> 5) & 1}")
        
        elif address == 0x10003:  # CONFIG0
            print(f"PROTECTED: {(value >> 2) & 1}")
            print(f"TX_CUT_THROUGH: {(value >> 4) & 1}")
            print(f"RX_CUT_THROUGH: {(value >> 5) & 1}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 lan8651_kernelfs.py <read|list> [address]")
        print("Examples:")
        print("  python3 lan8651_kernelfs.py read 0x10000")
        print("  python3 lan8651_kernelfs.py list")
        return
    
    debugfs = LAN8651Debugfs()
    
    if sys.argv[1] == "list":
        print("\nKnown LAN8651 Registers:")
        registers = [
            (0x10000, "ID_REV", "Chip and Revision ID"),
            (0x10001, "STATUS0", "Status Register 0"),
            (0x10002, "STATUS1", "Status Register 1"), 
            (0x10003, "CONFIG0", "Configuration Register 0"),
            (0x10004, "CONFIG1", "Configuration Register 1"),
            (0x10020, "FIFO_SIZE", "FIFO Size Configuration"),
            (0x10021, "CHUNK_SIZE", "Chunk Size Configuration")
        ]
        
        for addr, name, desc in registers:
            print(f"  0x{addr:08x} - {name:12s} - {desc}")
    
    elif sys.argv[1] == "read":
        if len(sys.argv) != 3:
            print("Usage: python3 lan8651_kernelfs.py read <address>")
            return
        
        address = int(sys.argv[2], 0)
        value = debugfs.read_register(address)
        
        if value is not None:
            show_register_info(address, value)
        else:
            print("\nTo enable register access, you need to:")
            print("1. Ensure debugfs is mounted: mount -t debugfs none /sys/kernel/debug")
            print("2. Add register access support to lan865x driver")
            print("3. Or use the ethtool approach with driver extension")

if __name__ == "__main__":
    main()