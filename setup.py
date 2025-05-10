from setuptools import setup, find_packages

setup(
    name="Tank game", 
    version="1.0.0",
    description="Tank game inspired by wii tanks",
    author="Frode Henrol",
    packages=find_packages(),
    install_requires=[
        "pygame==2.6.1",
        "numpy==1.26.4",
        "scipy==1.13.0",
        "triangle==20250106"
    ],
    entry_points={
        "console_scripts": [
            "tank_game = tank_game.main:main",
        ]
    },
    license="GPL-3.0",
    python_requires='>=3.8',
)
