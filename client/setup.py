from setuptools import setup
import ledscreen


setup(
    name='ledscreen',
    version=ledscreen.__version__,
    description='Student API for Henderson\'s LED screen',
    author=ledscreen.__author__,
    author_email='jacoblj3333@gmail.com',
    url='https://instancegaming.net',
    packages=['ledscreen'],
    install_requires=['zmq'],
    python_requires='>=3.6.0',
    classifiers=[
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ]
)
