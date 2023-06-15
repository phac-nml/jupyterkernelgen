from setuptools import setup

setup(
    name='jupyterkernelgen',
    version='0.1.0',
    description='A guided jupyter kernel creator',
    url='https://github.com/phac-nml/jupyterkernelgen',
    author='Public Health Agency of Canada',
    packages=['jupyterkernelgen'],
    entry_points= {
        'console_scripts': ['jupyterkernelgen=jupyterkernelgen.jupyterkernelgen:main']
    }
)
