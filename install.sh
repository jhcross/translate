#!/bin/bash

pushd ~
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
chmod +x miniconda.sh
./miniconda.sh -b -p ~/miniconda
rm miniconda.sh
popd

. ~/miniconda/bin/activate

export CONDA_PATH="$(dirname $(which conda))/../" # [anaconda root directory]

# Install basic PyTorch dependencies
conda install numpy pyyaml mkl mkl-include setuptools cmake cffi typing

# Add LAPACK support for the GPU
conda install -c pytorch magma-cuda80 # or magma-cuda90 if CUDA 9

yes | pip uninstall torch
yes | pip uninstall torch

# Install NCCL2
wget https://s3.amazonaws.com/pytorch/nccl_2.1.15-1%2Bcuda8.0_x86_64.txz
tar --no-same-owner -xvf nccl_2.1.15-1+cuda8.0_x86_64.txz
export NCCL_ROOT_DIR="$(pwd)/nccl_2.1.15-1+cuda8.0_x86_64"
export LD_LIBRARY_PATH="${NCCL_ROOT_DIR}/lib:${LD_LIBRARY_PATH}"
rm nccl_2.1.15-1+cuda8.0_x86_64.txz

git clone --recursive https://github.com/pytorch/pytorch
pushd pytorch
# PyTorch build from source
NCCL_ROOT_DIR="${NCCL_ROOT_DIR}" python3 setup.py install

# Caffe2 build from source (with ATen)
#CMAKE_ARGS=-DUSE_ATEN=ON python setup_caffe2.py install
mkdir -p build_caffe2 && pushd build_caffe2
cmake -DUSE_ATEN=ON -DCMAKE_PREFIX_PATH=$CONDA_PATH -DCMAKE_INSTALL_PATH=$CONDA_PATH
make DESTDIR=$CONDA_PATH install -j8 2>&1 | tee MAKE_OUT
popd
popd

export LD_LIBRARY_PATH=$CONDA_PATH/lib:$LD_LIBRARY_PATH

# Install ONNX
git clone https://github.com/onnx/onnx.git
pip install onnx

yes | pip uninstall fbtranslate
python3 setup.py build develop

pushd cpp
cmake -DCMAKE_PREFIX_PATH==$CONDA_PATH/usr/local -DCMAKE_INSTALL_PATH==$CONDA_PATH .
make
popd
