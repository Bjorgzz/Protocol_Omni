@echo -off
rem ============================================================================
rem  OPERATION VELOCITY EXTREME - AI-Priority BIOS Optimization
rem  WRX90E-SAGE-SE BIOS 1203 | Threadripper PRO 9995WX
rem  Generated: 2026-01-29
rem  Settings: 130+ AI-critical offsets from IFR extraction
rem  
rem  WARNING: 1400W PPT, security disabled, aggressive timings
rem           Requires 13C liquid cooling for sustained operation!
rem ============================================================================

echo ============================================
echo   PHASE 1: CPU Power Unlocking
echo ============================================
rem OC Mode = Customized (0x05)
setup_var.efi 0x051 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247
rem PPT Control = Manual
setup_var.efi 0x418 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem PPT = 1400W (0x578 little-endian)
setup_var.efi 0x419 0x78 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41A 0x05 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x41C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem TDP Control = Manual
setup_var.efi 0x413 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem TDP = 350W (0x15E little-endian)
setup_var.efi 0x414 0x5E -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x415 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x416 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x417 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem BoostFmaxEn = Manual
setup_var.efi 0x427 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem BoostFmax = 5700 MHz (0x1644)
setup_var.efi 0x428 0x44 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x429 0x16 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42A 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x42B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 2: C-States Disabled (AI Critical)
echo ============================================
rem Global C-State = Disabled (eliminates core wake latency)
setup_var.efi 0x024 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem DF C-States = Disabled (Data Fabric always awake)
setup_var.efi 0x42D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Power Supply Idle = Typical Current (0x00)
setup_var.efi 0x025 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem APBDIS = 1 (completely disable DF P-state transitions)
setup_var.efi 0x424 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem DF PState Freq Optimizer = Disabled
setup_var.efi 0x42C 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Power Down Enable = Disabled (memory stays active)
setup_var.efi 0x227 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Determinism Control = Manual
setup_var.efi 0x422 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Determinism = Power (sustained throughput)
setup_var.efi 0x423 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 3: CPU Scheduling and Boost
echo ============================================
rem Core Performance Boost = Auto (allows max clocks)
setup_var.efi 0x023 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem CPPC = Enabled
setup_var.efi 0x42E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem CPPC Preferred Cores = Enabled
setup_var.efi 0x42F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem HSMP Support = Enabled
setup_var.efi 0x430 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 4: Prefetchers (AI Streaming Critical)
echo ============================================
rem L1 Stream HW Prefetcher = Enabled
setup_var.efi 0x05D 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem L1 Stride Prefetcher = Enabled
setup_var.efi 0x05E 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem L1 Region Prefetcher = Enabled
setup_var.efi 0x05F 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem L2 Stream HW Prefetcher = Enabled
setup_var.efi 0x060 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem L2 Up/Down Prefetcher = Enabled
setup_var.efi 0x061 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem L1 Burst Prefetch Mode = Enabled
setup_var.efi 0x062 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 5: NUMA and Memory Fabric
echo ============================================
rem NPS = NPS1 (single NUMA domain)
setup_var.efi 0x075 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Memory Interleaving = Enabled
setup_var.efi 0x076 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Interleave Region Size = 2KB (optimal for streaming)
setup_var.efi 0x078 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem DRAM Map Inversion = Disabled
setup_var.efi 0x07B 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Address Hash Bank = Enabled
setup_var.efi 0x221 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Address Hash CS = Enabled
setup_var.efi 0x222 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Chipselect Interleaving = Enabled
setup_var.efi 0x220 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 6: Memory Scrubbing Disabled
echo ============================================
rem DRAM Scrub Time = Disabled
setup_var.efi 0x28C 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Redirect Scrubber = Disabled
setup_var.efi 0x28A 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Memory Clear = Disabled (faster boot)
setup_var.efi 0x286 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem ECC = Enabled (data integrity)
setup_var.efi 0x283 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem UECC Retry = Enabled
setup_var.efi 0x284 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 7: PCIe P2P (Multi-GPU Critical)
echo ============================================
rem IOMMU = Disabled (direct GPU-GPU path)
setup_var.efi 0x377 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem ACS = Disabled (allow P2P across PCIe)
setup_var.efi 0x341 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem PCIe ARI Enumeration = Enabled
setup_var.efi 0x343 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem PCIe ARI Support = Enabled
setup_var.efi 0x344 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem Above 4G Decoding = Enabled (Setup VarStore!)
setup_var.efi 0x102 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9
rem Relaxed Ordering = Enabled (better PCIe throughput)
setup_var.efi 0x10B 0x01 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9
rem AtomicOp = Enabled (GPU atomic operations)
setup_var.efi 0x35B 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem ASPM = Disabled (no PCIe power management)
setup_var.efi 0x34D 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 8: Security Disabled (Performance)
echo ============================================
rem SMEE = Disabled (no memory encryption)
setup_var.efi 0x036 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem SEV Control = Disabled
setup_var.efi 0x037 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
rem SEV-SNP = Disabled
setup_var.efi 0x374 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
rem TSME = Disabled
setup_var.efi 0x2F9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo ============================================
echo   PHASE 9: Memory Timings
echo ============================================
rem PRIMARY: tCL=34, tRCD=34, tRP=34, tRAS=68, tRC=102
setup_var.efi 0x2A7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2A8 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2A9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AA 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AB 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AC 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AD 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AE 0x22 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2AF 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B0 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B1 0x44 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B2 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B3 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B4 0x66 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B5 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem SECONDARY: tWR=42, tRFC1=420, tRFC2=320, tRFCsb=240, tCWL=32, tRTP=10
setup_var.efi 0x2B6 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B7 0x2A -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B8 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2B9 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BA 0xA4 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BC 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BD 0x40 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BE 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2BF 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C0 0xF0 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C1 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C2 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C3 0x20 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C4 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C5 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C6 0x0A -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C7 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem ROW/BURST: tRRD_L=6, tRRD_S=4, tFAW=16, tWTR_L=12, tWTR_S=4
setup_var.efi 0x2C8 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2C9 0x06 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CA 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CC 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CD 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CE 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2CF 0x10 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D0 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D1 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D2 0x0C -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D3 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D4 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D5 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D6 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

rem TURNAROUND: tRDRD=1/1/4/4, tWRWR=1/1/4/4, tWRRD=2, tRDWR=8
setup_var.efi 0x2D7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D8 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2D9 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DA 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DB 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DC 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DD 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DE 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2DF 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E0 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E1 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E2 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E3 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E4 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E5 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E6 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E7 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E8 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2E9 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EA 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EB 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EC 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2ED 0x04 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EE 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2EF 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F0 0x02 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F1 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F2 0x01 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F3 0x08 -g 3A997502-647A-4C82-998E-52EF9486A247
setup_var.efi 0x2F4 0x00 -g 3A997502-647A-4C82-998E-52EF9486A247

echo.
echo ============================================
echo   EXTREME SETTINGS APPLIED!
echo ============================================
echo.
echo REMAINING MANUAL STEPS (BIOS UI required):
echo.
echo 1. Extreme Tweaker - DRAM Timing:
echo    tREFI = 65535 (CRITICAL - +15-20 pct bandwidth)
echo.
echo 2. AMD Overclocking - Precision Boost:
echo    PPT Limit  = 1400W
echo    TDC Limit  = 1000A
echo    EDC Limit  = 1400A
echo    PBO Scalar = 10X
echo.
echo 3. AMD Overclocking - Curve Optimizer:
echo    All Cores = -35 to -50 (test stability)
echo.
echo 4. AMD CBS - DF Common Options:
echo    FCLK = 2100 MHz (match 12-channel DDR5-6000)
echo.
echo ============================================
echo Type 'reset' to reboot and apply changes
echo ============================================
