#!/bin/bash
ssh omni@100.94.47.77 "uptime && mokutil --sb-state && nvidia-smi -L"
