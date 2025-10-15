"""Setup para instalação do app_precos_claude como pacote."""
from setuptools import setup, find_packages

setup(
    name="app_precos_claude",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    python_requires=">=3.12",
)
