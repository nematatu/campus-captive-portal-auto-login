#!/usr/bin/env bash

set -euo pipefail

ENV_NAME="playwright"

echo "=== Create conda environment ==="

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
    echo "Conda environment '${ENV_NAME}' already exists."
else
    conda create -y -n "${ENV_NAME}" python=3.12
fi

echo "=== Activate conda environment ==="
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

echo "=== Install Python packages ==="
pip install -r requirements.txt

echo "=== Install Playwright Chromium ==="
playwright install chromium

echo "=== Install system dependencies ==="
sudo apt update

if apt-cache show libasound2t64 >/dev/null 2>&1; then
    sudo apt install -y \
        libnspr4 \
        libnss3 \
        libatk-bridge2.0-0 \
        libxkbcommon0 \
        libgbm1 \
        libasound2t64
else
    sudo apt install -y \
        libnspr4 \
        libnss3 \
        libatk-bridge2.0-0 \
        libxkbcommon0 \
        libgbm1 \
        libasound2
fi

echo "=== Run test ==="
python test.py

echo
echo "Done. login.png should have been created."
