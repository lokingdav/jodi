pip install --upgrade build setuptools wheel

git clone https://github.com/lokingdav/libcpex.git 
cd libcpex

python -m build
pip install dist/*.whl

cd .. && rm -rf libcpex