# WRX90 BIOS IFR Analysis - AI Optimization Settings

**Source**: Pro-WS-WRX90E-SAGE-SE-ASUS-1203.CAP (BIOS 1203)
**Total Settings Found**: 2011
**Analysis Date**: 2026-01-29

## VarStore Reference

| VarID | VarStore Name | GUID | Purpose |
|-------|---------------|------|---------|
| 5 | Setup | EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9 | Main BIOS settings |
| 16 | AmdSetupSHP | 3A997502-647A-4C82-998E-52EF9486A247 | Shimada Peak (Zen5) CBS settings |
| 17 | AmdSetupSTP | 3A997502-647A-4C82-998E-52EF9486A247 | Storm Peak (older) CBS settings |
| 15 | AMD_PBS_SETUP | A339D746-F678-49B3-9FC7-54CE0F9DF226 | AMD Platform BIOS Settings |
| 18 | ServerSetup | 01239999-FC0E-4B6E-9E79-D54D5DB6CD20 | Server/workstation settings |

---

## AI-Critical Settings (Priority Order)

### 1. CPU Power Management

| Setting | QuestionID | VarStore | Offset | Width | Value for AI |
|---------|------------|----------|--------|-------|--------------|
| OC Mode | CbsCmnCpuOcModeSHP | AmdSetupSHP (16) | 81 | 1 | 5 (Customized) |
| PPT Control | CbsCmnPPTCtlSHP | AmdSetupSHP (16) | 1048 | 1 | 1 (Manual) |
| PPT Limit (W) | CbsCmnPPTLimitSHP | AmdSetupSHP (16) | 1049 | 4 | 1400 (0x578) |
| TDP Limit (W) | CbsCmnTDPLimitSHP | AmdSetupSHP (16) | 1044 | 4 | 350 |
| DF C-States | CbsCmnGnbSmuDfCstatesSHP | AmdSetupSHP (16) | 1069 | 1 | 0 (Disabled) **CRITICAL** |
| Global C-State | CbsCmnCpuGlobalCstateCtrlSHP | AmdSetupSHP (16) | 35 | 1 | 0 (Disabled) |
| CPU Core Boost | CbsCmnCpuCpbSHP | AmdSetupSHP (16) | 34 | 1 | 1 (Enabled) |

### 2. Memory/Data Fabric (Bandwidth Critical)

| Setting | QuestionID | VarStore | Offset | Width | Value for AI |
|---------|------------|----------|--------|-------|--------------|
| NUMA Nodes (NPS) | CbsDfCmnDramNpsSHP | AmdSetupSHP (16) | 117 (0x75) | 1 | 1 (NPS1) |
| Memory Interleaving | CbsDfCmnMemIntlvSHP | AmdSetupSHP (16) | 118 (0x76) | 1 | 1 (Enabled) |
| Memory Interleaving Size | CbsDfCmnMemIntlvPageSizeSHP | AmdSetupSHP (16) | 120 (0x78) | 1 | 1 (2KB) |
| tRFC1 | CbsCmnMemTimingTrfc1DdrSHP | AmdSetupSHP (16) | 698 (0x2BA) | 2 | 420 (0x1A4) |
| tRFC2 | CbsCmnMemTimingTrfc2DdrSHP | AmdSetupSHP (16) | 701 (0x2BD) | 2 | 320 (0x140) |
| tRFCSb | CbsCmnMemTimingTrfcSbDdrSHP | AmdSetupSHP (16) | 704 (0x2C0) | 2 | 240 (0xF0) |

### 3. PCIe/GPU P2P (Multi-GPU Critical)

| Setting | QuestionID | VarStore | Offset | Width | Value for AI |
|---------|------------|----------|--------|-------|--------------|
| IOMMU | CbsCmnGnbNbIOMMUSHP | AmdSetupSHP (16) | 887 (0x377) | 1 | 0 (Disabled) **P2P Critical** |
| ACS Enable | CbsCmnGnbACSEnableSHP | AmdSetupSHP (16) | 833 (0x341) | 1 | 0 (Disabled) **P2P Critical** |
| PCIe ARI | CbsCmnGnbPcieAriEnumerationSHP | AmdSetupSHP (16) | 835 (0x343) | 1 | 1 (Enabled) |
| Above 4G Decode | PCIS006 | Setup (5) | 258 (0x102) | 1 | 1 (Enabled) |

### 4. CPU Prefetchers (AI Streaming Critical)

| Setting | QuestionID | VarStore | Offset | Width | Value for AI |
|---------|------------|----------|--------|-------|--------------|
| L1 Stream Prefetcher | CbsCmnCpuL1StreamHwPrefetcherSHP | AmdSetupSHP (16) | 93 (0x5D) | 1 | 1 (Enabled) |
| L1 Stride Prefetcher | CbsCmnCpuL1StridePrefetcherSHP | AmdSetupSHP (16) | 94 (0x5E) | 1 | 1 (Enabled) |
| L1 Region Prefetcher | CbsCmnCpuL1RegionPrefetcherSHP | AmdSetupSHP (16) | 95 (0x5F) | 1 | 1 (Enabled) |
| L2 Stream Prefetcher | CbsCmnCpuL2StreamHwPrefetcherSHP | AmdSetupSHP (16) | 96 (0x60) | 1 | 1 (Enabled) |
| L2 Up/Down Prefetcher | CbsCmnCpuL2UpDownPrefetcherSHP | AmdSetupSHP (16) | 97 (0x61) | 1 | 1 (Enabled) |
| L1 Burst Prefetch Mode | CbsCmnCpuL1BurstPrefetchModeSHP | AmdSetupSHP (16) | 98 (0x62) | 1 | 1 (Enabled) |

---

## EFI Shell Commands for AI Optimization

**VarStores used:**
- **AmdSetupSHP** (GUID: `3A997502-647A-4C82-998E-52EF9486A247`) — AMD CBS settings (PPT, TDP, C-States, prefetchers)
- **Setup** (GUID: `EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9`) — Platform settings (Above 4G Decoding)

**Full batch script**: `tools/bios/nuclear_settings.nsh` (EFI Shell format)

```bash
# Key commands (excerpt from nuclear_settings.nsh):

# PPT 1400W (Manual mode + 4-byte value) - AmdSetupSHP
setup_var.efi 0x418 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # PPT Control = Manual
setup_var.efi 0x419 0x78 -g 3A997502-647A-4C82-998E-52EF9486A247  # 1400 = 0x0578 (byte 0)
setup_var.efi 0x41A 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 1)
setup_var.efi 0x41B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 2)
setup_var.efi 0x41C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 3)

# TDP 350W (4-byte value) - AmdSetupSHP
setup_var.efi 0x414 0x5E -g 3A997502-647A-4C82-998E-52EF9486A247  # 350 = 0x015E (byte 0)
setup_var.efi 0x415 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 1)
setup_var.efi 0x416 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 2)
setup_var.efi 0x417 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247  # (byte 3)

# DF C-States Disabled (CRITICAL for AI bandwidth)
setup_var.efi 0x42D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# Global C-State Disabled
setup_var.efi 0x23 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# IOMMU Disabled (P2P GPU communication)
setup_var.efi 0x377 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# ACS Disabled (Direct GPU-GPU path)
setup_var.efi 0x341 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

# NPS1 Mode (Single NUMA domain)
setup_var.efi 0x75 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

# All prefetchers enabled (offsets 0x5D-0x62)
setup_var.efi 0x5D 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Stream
setup_var.efi 0x5E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Stride
setup_var.efi 0x5F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Region
setup_var.efi 0x60 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L2 Stream
setup_var.efi 0x61 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L2 Up/Down
setup_var.efi 0x62 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247  # L1 Burst

# Above 4G Decoding - Setup VarStore (explicit GUID required)
setup_var.efi 0x102 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9
```

---

## Hidden Settings Not in Redfish (IFR-Only)

These settings are in the BIOS but may not be exposed via Redfish API:

1. **DF Sync Flood Propagation** - Error handling for Data Fabric
2. **CCD Bandwidth Throttle** - Per-CCD bandwidth limits
3. **Clean Victim FTI Command Balance** - Cache coherency tuning
4. **Memory Scrambler** - Security feature that can impact performance
5. **CPPC Preferred Cores** - OS scheduler hints
6. **Determinism Control** - Power vs performance bias
7. **SVI3 SVC Speed Control** - Voltage regulator communication speed

---

## Files Generated

- `wrx90_ifr_full.json` - Complete IFR database (33,006 lines, 2011 settings)
- `nuclear_settings.nsh` - EFI Shell script for AI optimization (.nsh = native EFI format)
- `Pro-WS-WRX90E-SAGE-SE-ASUS-1203.CAP.report.txt` - UEFIExtract report
- `Pro-WS-WRX90E-SAGE-SE-ASUS-1203.CAP.guids.csv` - GUID mappings

## USB Preparation for EFI Shell Execution

```
USB Drive (FAT32):
├── EFI/
│   ├── BOOT/
│   │   └── BOOTX64.EFI    # Shell.efi renamed (from EDK2 releases)
│   └── Tools/
│       ├── setup_var.efi  # From datasone/setup_var.efi releases
│       └── nuclear_settings.nsh  # Copy from this directory
```

**Execution Steps:**
1. Format USB as FAT32, create directory structure above
2. Download Shell.efi from tianocore/edk2 releases → rename to BOOTX64.EFI
3. Download setup_var.efi from datasone/setup_var.efi releases
4. Copy `nuclear_settings.nsh` to USB
5. Access BMC KVM, reboot server
6. Press F8 during POST → Boot Menu → Select USB
7. In EFI Shell: `fs0:`, `cd EFI\Tools`, then `nuclear_settings.nsh` (or run commands individually)
8. Type `reset` to reboot, verify settings via Redfish/BIOS

