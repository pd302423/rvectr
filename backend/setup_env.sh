#!/bin/bash
set -e

echo "Setting up EasyMocap virtual environment..."
cd EasyMocap
python3.11 -m venv venv
source venv/bin/activate

# Install core dependencies (PyTorch should be installed based on your system's CUDA version)
# You might want to customize the PyTorch install command below for your specific setup.
echo "Installing pip requirements..."
pip install --upgrade pip
pip install -r requirements.txt
pip install --no-build-isolation chumpy
pip install trimesh # needed for the obj to glb conversion

echo "Installing EasyMocap as a package..."
python setup.py install

echo ""
echo "========================================"
echo "EasyMocap setup complete."
echo "To activate this environment in the future, run:"
echo "source EasyMocap/venv/bin/activate"
echo "========================================"
