pip install --upgrade build setuptools wheel

git clone https://github.com/lokingdav/libjodi.git 
cd libjodi

python -m build
pip install dist/*.whl

cd .. && rm -rf libjodi