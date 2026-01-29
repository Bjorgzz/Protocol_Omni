@echo -off
rem WRX90 AI NUCLEAR BIOS Settings - EFI Shell Script
rem BIOS: ASUS WRX90E-SAGE-SE v1203 (ShimadaPeakPI-SP6_1.0.0.1a_PatchA)
rem Generated: 2026-01-29 from IFR extraction
rem Target: Maximum AI/LLM inference throughput
rem
rem VarStores:
rem   Setup (VarID 5): EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9
rem   AmdSetupSHP (VarID 16): 3A997502-647A-4C82-998E-52EF9486A247
rem
rem CRITICAL WARNING: These settings are for 13C liquid-chilled system with
rem extreme power delivery. DO NOT apply to stock-cooled systems.
rem
rem Usage: fs0:\EFI\Tools\nuclear_settings.nsh
rem Or execute commands line-by-line manually

rem ==== VarStore: AmdSetupSHP (GUID: 3A997502-647A-4C82-998E-52EF9486A247) ====

rem --- CPU POWER MANAGEMENT ---
rem OC Mode = Customized (offset 81 = 0x51)
setup_var.efi 0x51 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247

rem PPT Control = Manual (offset 1048 = 0x418)
setup_var.efi 0x418 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem PPT Limit = 1400W (offset 1049 = 0x419, 4 bytes little-endian: 0x78 0x05 0x00 0x00)
setup_var.efi 0x419 0x78 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41A 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem TDP Limit = 350W (offset 1044 = 0x414, 4 bytes little-endian: 0x5E 0x01 0x00 0x00)
setup_var.efi 0x414 0x5E -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x415 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x416 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x417 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem CPU Core Boost = Enabled (offset 34 = 0x22)
setup_var.efi 0x22 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Global C-State Control = Disabled (offset 35 = 0x23) - AI CRITICAL
setup_var.efi 0x23 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem DF C-States = Disabled (offset 1069 = 0x42D) - AI CRITICAL BANDWIDTH KILLER
setup_var.efi 0x42D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem --- CPU PREFETCHERS (ALL ENABLED FOR AI STREAMING) ---
rem L1 Stream HW Prefetcher = Enabled (offset 93 = 0x5D)
setup_var.efi 0x5D 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem L1 Stride Prefetcher = Enabled (offset 94 = 0x5E)
setup_var.efi 0x5E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem L1 Region Prefetcher = Enabled (offset 95 = 0x5F)
setup_var.efi 0x5F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem L2 Stream HW Prefetcher = Enabled (offset 96 = 0x60)
setup_var.efi 0x60 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem L2 Up/Down Prefetcher = Enabled (offset 97 = 0x61)
setup_var.efi 0x61 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem L1 Burst Prefetch Mode = Enabled (offset 98 = 0x62)
setup_var.efi 0x62 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem --- MEMORY / DATA FABRIC ---
rem NUMA Nodes (NPS) = NPS1 (offset 117 = 0x75)
setup_var.efi 0x75 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Memory Interleaving = Enabled (offset 118 = 0x76)
setup_var.efi 0x76 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem Memory Interleaving Region Size = 2KB (offset 120 = 0x78)
setup_var.efi 0x78 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRFC1 = 420 (offset 698 = 0x2BA, 2 bytes: 0xA4 0x01)
setup_var.efi 0x2BA 0xA4 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRFC2 = 320 (offset 701 = 0x2BD, 2 bytes: 0x40 0x01)
setup_var.efi 0x2BD 0x40 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BE 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem tRFCSb = 240 (offset 704 = 0x2C0, 2 bytes: 0xF0 0x00)
setup_var.efi 0x2C0 0xF0 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C1 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem --- PCIe / GPU P2P ---
rem IOMMU = Disabled (offset 887 = 0x377) - P2P CRITICAL
setup_var.efi 0x377 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ACS Enable = Disabled (offset 833 = 0x341) - P2P CRITICAL
setup_var.efi 0x341 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem PCIe ARI Enumeration = Enabled (offset 835 = 0x343)
setup_var.efi 0x343 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ==== VarStore: Setup (GUID: EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9) ====
rem Above 4G Decoding = Enabled (offset 258 = 0x102) - REQUIRED FOR MULTI-GPU
setup_var.efi 0x102 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9

echo AI NUCLEAR settings applied. Reboot to activate.
echo.
echo MANUAL SETTINGS REQUIRED (BIOS UI only):
echo   1. tREFI = 65535 (Advanced - AMD CBS - UMC Common - DDR Timing)
echo   2. Curve Optimizer per-core offsets (Advanced - AMD Overclocking)
echo   3. PBO Scalar = 10x (Advanced - AMD Overclocking - PBO)
