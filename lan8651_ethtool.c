// SPDX-License-Identifier: GPL-2.0+
/*
 * LAN8651 Register Access via existing network interface
 * 
 * Uses ethtool private ioctls for register access
 * No need for separate kernel module
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <linux/if.h>
#include <linux/sockios.h>
#include <linux/ethtool.h>

#define MAX_INTERFACES 10

struct lan8651_reg_access {
    __u32 cmd;
    __u32 address;
    __u32 value;
};

#define ETHTOOL_GLANREG     0x00001000  /* Get LAN register */
#define ETHTOOL_SLANREG     0x00001001  /* Set LAN register */

int find_lan8651_interface(char *ifname, size_t ifname_size) {
    FILE *fp;
    char line[256];
    
    fp = fopen("/proc/net/dev", "r");
    if (!fp) {
        perror("Cannot open /proc/net/dev");
        return -1;
    }
    
    // Skip header lines
    fgets(line, sizeof(line), fp);
    fgets(line, sizeof(line), fp);
    
    while (fgets(line, sizeof(line), fp)) {
        char *iface = strtok(line, ":");
        if (iface && strstr(iface, "eth")) {
            // Check if this interface uses lan865x driver
            char driver_path[512];
            char driver_name[64];
            FILE *driver_fp;
            
            snprintf(driver_path, sizeof(driver_path), 
                    "/sys/class/net/%s/device/driver/module", 
                    iface + (iface[0] == ' ' ? 1 : 0));
            
            if (readlink(driver_path, driver_name, sizeof(driver_name)) > 0) {
                if (strstr(driver_name, "lan865x")) {
                    strncpy(ifname, iface + (iface[0] == ' ' ? 1 : 0), ifname_size);
                    fclose(fp);
                    return 0;
                }
            }
        }
    }
    
    fclose(fp);
    return -1;
}

int lan8651_read_register(const char *ifname, u_int32_t address, u_int32_t *value) {
    int sock;
    struct ifreq ifr;
    struct ethtool_drvinfo drvinfo;
    struct lan8651_reg_access reg_access;
    
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("socket");
        return -1;
    }
    
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    
    // First check if this is really a lan865x interface
    drvinfo.cmd = ETHTOOL_GDRVINFO;
    ifr.ifr_data = (char *)&drvinfo;
    
    if (ioctl(sock, SIOCETHTOOL, &ifr) < 0) {
        perror("ETHTOOL_GDRVINFO ioctl");
        close(sock);
        return -1;
    }
    
    if (strcmp(drvinfo.driver, "lan865x") != 0) {
        fprintf(stderr, "Interface %s is not using lan865x driver\n", ifname);
        close(sock);
        return -1;
    }
    
    // Now try to read register (this would need driver support)
    reg_access.cmd = ETHTOOL_GLANREG;
    reg_access.address = address;
    reg_access.value = 0;
    
    ifr.ifr_data = (char *)&reg_access;
    
    if (ioctl(sock, SIOCETHTOOL, &ifr) < 0) {
        perror("Register read ioctl - driver extension needed");
        close(sock);
        return -1;
    }
    
    *value = reg_access.value;
    close(sock);
    return 0;
}

int lan8651_write_register(const char *ifname, u_int32_t address, u_int32_t value) {
    int sock;
    struct ifreq ifr;
    struct lan8651_reg_access reg_access;
    
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("socket");
        return -1;
    }
    
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    
    reg_access.cmd = ETHTOOL_SLANREG;
    reg_access.address = address;
    reg_access.value = value;
    
    ifr.ifr_data = (char *)&reg_access;
    
    if (ioctl(sock, SIOCETHTOOL, &ifr) < 0) {
        perror("Register write ioctl - driver extension needed");
        close(sock);
        return -1;
    }
    
    close(sock);
    return 0;
}

int main(int argc, char *argv[]) {
    char ifname[IFNAMSIZ];
    u_int32_t address, value;
    int ret;
    
    if (argc < 2) {
        printf("Usage: %s <read|write> [address] [value]\n", argv[0]);
        printf("Example: %s read 0x10000\n", argv[0]);
        printf("Example: %s write 0x10000 0x0C\n", argv[0]);
        return 1;
    }
    
    // Find LAN8651 interface
    if (find_lan8651_interface(ifname, sizeof(ifname)) < 0) {
        fprintf(stderr, "No LAN8651 interface found\n");
        return 1;
    }
    
    printf("Using interface: %s\n", ifname);
    
    if (strcmp(argv[1], "read") == 0) {
        if (argc != 3) {
            printf("Usage: %s read <address>\n", argv[0]);
            return 1;
        }
        
        address = strtoul(argv[2], NULL, 0);
        ret = lan8651_read_register(ifname, address, &value);
        if (ret == 0) {
            printf("READ 0x%08X = 0x%08X (%u)\n", address, value, value);
        } else {
            printf("ERROR: Read failed\n");
        }
    }
    else if (strcmp(argv[1], "write") == 0) {
        if (argc != 4) {
            printf("Usage: %s write <address> <value>\n", argv[0]);
            return 1;
        }
        
        address = strtoul(argv[2], NULL, 0);
        value = strtoul(argv[3], NULL, 0);
        ret = lan8651_write_register(ifname, address, value);
        if (ret == 0) {
            printf("WRITE 0x%08X = 0x%08X - OK\n", address, value);
        } else {
            printf("ERROR: Write failed\n");
        }
    }
    else {
        printf("Unknown command: %s\n", argv[1]);
        return 1;
    }
    
    return ret;
}