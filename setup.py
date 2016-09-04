from distutils.core import setup


setup(
    name='Adafruit-upy_tsl2561',
    py_modules=['tsl2561'],
    version="1.0",
    description="Driver for MicroPython for the tsl2561 light sensor.",
    long_description="""\
This library lets you communicate with a TSL2561 light sensor.
""",
    author='Radomir Dopieralski',
    author_email='micropython@sheep.art.pl',
    classifiers = [
        'Development Status :: 6 - Mature',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
)
