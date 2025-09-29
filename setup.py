from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="hyperate",
    version="1.0.0",
    description="Python client for the HypeRate WebSocket API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Serpensin",
    author_email="serpensin@serpensin.com",
    packages=find_packages(where="lib"),
    package_dir={"": "lib"},
    install_requires=[
        "websockets>=10.0",
    ],
    python_requires=">=3.8",
    license="MIT",
    license_files=("LICENSE",),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Libraries",
        "Topic :: Communications :: Conferencing",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
    url="https://hyperate.io/",
    project_urls={
        "Documentation": "https://github.com/Serpensin/HypeRate-Python#readme",
        "Source": "https://github.com/Serpensin/HypeRate-Python",
        "Homepage": "https://hyperate.io/",
        "Bug Reports": "https://github.com/Serpensin/HypeRate-Python/issues",
    },
)
