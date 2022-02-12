from setuptools import find_packages, setup

with open('requirements.txt') as f:
  required = f.read().splitlines()

setup(
  name='stockcv',
  version='1.0',
  description='use stock as lfo',
  author='Max Knutsen',
  packages=["stockcv"],
  install_requires=required,   
  entry_points={
    'console_scripts': [
      'run-flask-thing=stockcv.flask_entry:main'
    ]
  }
)
