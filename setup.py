from setuptools import setup, find_packages
import pathlib
import re

WORK_DIR = pathlib.Path(__file__).parent

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

__version__ = ""
exec(open('efb_wechat_slave/__version__.py').read())


setup(
    name="efb-wechat-slave",
    version=__version__,
    description='EFB Slave for WeChat on CuteCat iHttp plugin',
    author='honus',
    author_email="undefined@example.com",
    url="https://github.com/honus/efb-wechac-slave",
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    python_requires='>=3.7',
    keywords=["wechat", ],
    install_requires=[
        "python-CuteCat-iHttp",
        "ehforwarderbot",
        "PyYaml>=5.3",
        "cachetools",
        "requests",
        "python-magic",
        "lxml"
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: User Interfaces',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        "Operating System :: OS Independent"
    ],
    entry_points={
        'ehforwarderbot.slave': 'honus.CuteCatiHttp = efb_wechat_slave:CuteCatChannel',
    }
)