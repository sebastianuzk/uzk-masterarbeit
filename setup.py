from setuptools import setup, find_packages

setup(
    name="uzk-masterarbeit",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "aiohttp",
        "beautifulsoup4",
        "robotexclusionrulesparser",
        "chromadb",
        "sentence-transformers",
    ],
)