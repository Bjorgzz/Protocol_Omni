@echo -off
rem Export AI-Critical BIOS Settings to Screen
rem Run: fs0:\EFI\Tools\export_settings.nsh
rem Photo the output or redirect: export_settings.nsh > fs0:\export.txt

echo === AI-Critical Settings Export ===
echo.

rem === AmdSetupSHP VarStore (GUID: 3A997502-647A-4C82-998E-52EF9486A247) ===
echo --- CPU POWER ---
echo OC Mode (0x51):
setup_var.efi 0x51 -g 3A997502-647A-4C82-998E-52EF9486A247
echo PPT Control (0x418):
setup_var.efi 0x418 -g 3A997502-647A-4C82-998E-52EF9486A247
echo PPT Limit byte0 (0x419):
setup_var.efi 0x419 -g 3A997502-647A-4C82-998E-52EF9486A247
echo PPT Limit byte1 (0x41A):
setup_var.efi 0x41A -g 3A997502-647A-4C82-998E-52EF9486A247
echo PPT Limit byte2 (0x41B):
setup_var.efi 0x41B -g 3A997502-647A-4C82-998E-52EF9486A247
echo PPT Limit byte3 (0x41C):
setup_var.efi 0x41C -g 3A997502-647A-4C82-998E-52EF9486A247
echo TDP byte0 (0x414):
setup_var.efi 0x414 -g 3A997502-647A-4C82-998E-52EF9486A247
echo TDP byte1 (0x415):
setup_var.efi 0x415 -g 3A997502-647A-4C82-998E-52EF9486A247
echo TDP byte2 (0x416):
setup_var.efi 0x416 -g 3A997502-647A-4C82-998E-52EF9486A247
echo TDP byte3 (0x417):
setup_var.efi 0x417 -g 3A997502-647A-4C82-998E-52EF9486A247

echo.
echo --- C-STATES ---
echo DF C-States (0x42D):
setup_var.efi 0x42D -g 3A997502-647A-4C82-998E-52EF9486A247
echo Global C-State (0x23):
setup_var.efi 0x23 -g 3A997502-647A-4C82-998E-52EF9486A247

echo.
echo --- GPU P2P ---
echo IOMMU (0x377):
setup_var.efi 0x377 -g 3A997502-647A-4C82-998E-52EF9486A247
echo ACS (0x341):
setup_var.efi 0x341 -g 3A997502-647A-4C82-998E-52EF9486A247
echo PCIe ARI (0x343):
setup_var.efi 0x343 -g 3A997502-647A-4C82-998E-52EF9486A247

echo.
echo --- MEMORY ---
echo NPS Mode (0x75):
setup_var.efi 0x75 -g 3A997502-647A-4C82-998E-52EF9486A247
echo Mem Interleave (0x76):
setup_var.efi 0x76 -g 3A997502-647A-4C82-998E-52EF9486A247
echo Mem Intlv Size (0x78):
setup_var.efi 0x78 -g 3A997502-647A-4C82-998E-52EF9486A247

echo.
echo --- PREFETCHERS (ALL 6) ---
echo L1 Stream (0x5D):
setup_var.efi 0x5D -g 3A997502-647A-4C82-998E-52EF9486A247
echo L1 Stride (0x5E):
setup_var.efi 0x5E -g 3A997502-647A-4C82-998E-52EF9486A247
echo L1 Region (0x5F):
setup_var.efi 0x5F -g 3A997502-647A-4C82-998E-52EF9486A247
echo L2 Stream (0x60):
setup_var.efi 0x60 -g 3A997502-647A-4C82-998E-52EF9486A247
echo L2 Up/Down (0x61):
setup_var.efi 0x61 -g 3A997502-647A-4C82-998E-52EF9486A247
echo L1 Burst (0x62):
setup_var.efi 0x62 -g 3A997502-647A-4C82-998E-52EF9486A247

echo.
rem === Setup VarStore (GUID: EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9) ===
echo --- PCIE (Setup VarStore) ---
echo Above 4G Decode (0x102):
setup_var.efi 0x102 -g EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9

echo.
echo === Export Complete ===
