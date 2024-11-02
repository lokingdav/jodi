from setuptools import setup, find_packages

def parse_requirements(filename):
    """Load requirements from a pip requirements file."""
    with open(filename, 'r') as f:
        lines = f.readlines()
    requirements = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith(('#', '-', '--')):
            requirements.append(line)
    return requirements

requirements = parse_requirements('requirements.txt')

setup(
    name='cpex',
    version='0.1.0',
    packages=find_packages(),
    description='Control Plane Extension For Telephony',
    author='David L. Adei',
    author_email='lokingdav@gmail.com',
    url='https://github.com/lokingdav/cpex',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    install_requires=requirements,
    python_requires='>=3.8',
)
