# fbtranslate

## Installation instructions

### Install MiniConda3
```bash
pushd ~
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
chmod +x miniconda.sh
./miniconda.sh -b -p ~/miniconda
rm miniconda.sh
popd
```

### Install PyTorch and Caffe2
```bash

# Install basic PyTorch dependencies
conda install numpy pyyaml mkl mkl-include setuptools cmake cffi typing

# Add LAPACK support for the GPU
conda install -c pytorch magma-cuda80 # or magma-cuda90 if CUDA 9

pushd ~
git clone --recursive https://github.com/pytorch/pytorch
cd pytorch

# PyTorch build from source
python setup.py install

# Caffe2 build from source (with ATen)
CMAKE_ARGS=-DUSE_ATEN=ON python setup_caffe2.py install
popd
```

### Install ONNX
```bash
pushd ~
git clone --recursive https://github.com/onnx/onnx.git
pip install ./onnx
popd
```

### Install FBTranslate
```bash
. ~/miniconda/bin/activate
yes | pip uninstall fbtranslate
git clone --recursive https://github.com/facebookincubator/fbtranslate.git
cd fbtranslate
python3 setup.py build develop
```

## Training

We provide a example script to train a model for the IWSLT 2014 German-English task. We used this command to obtain [a pretrained model](TODO).

```
bash fbtranslate/examples/train_iwslt14.sh
```
