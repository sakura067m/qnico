from setuptools import setup
import platform
if "darwin" == platform.system().lower():
    # Mac needs certifi for ssl/https
    requirements = [
        "certifi",
        "PyQt5>=5.8.2",  # TBD
    ]
else:
    requirements = [
        "PyQt5>=5.8.2",  # TBD
    ]

setup(
    name="qnico",  # TBC
    version="0.1b4",
    description="get info and mp4 from niconico",
    url="https://github.com/sakura067m/qStream",
    author="sakura067m",
    author_email="3IE19001M@s.kyushu-u.ac.jp",
##    license='',  # TBD
    packages=["qnico"],
    package_dir={"qnico": "qnico"},
    package_data={
        "qStream":[]
    },
    entry_points={
        "gui_scripts": ["qnico = qnico.__main__:main"]
    },
    install_requires=requirements,
    keywords="niconico download dmc",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Developers",
    ],
)
