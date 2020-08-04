import setuptools
from greek_tv_dl._version import __VERSION__

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    requires = fh.readlines()

setuptools.setup(
    name='Greek TV Downloader',
    version=__VERSION__,
    scripts=['greek-tv-dl'],
    author="marios8543",
    author_email="marios8543@gmail.com",
    description="A downloader for many greek TV channels",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marios8543/Greek-TV-DL",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT License",
         "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "greek-tv-dl = greek_tv_dl.main:main"
        ]
    },
    install_requires=requires
)
