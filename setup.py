from setuptools import setup, find_packages

setup(
    name="kirn",
    version="0.1.0",
    description="⚡ Kirn — AI-Integrated Terminal",
    author="rahuldeepak-the-one",
    packages=find_packages(),
    install_requires=[
        "ollama",
        "prompt_toolkit>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "kirn=kirn.cli:main",
        ],
    },
    python_requires=">=3.10",
)
