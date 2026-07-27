from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="forensicsuite-sdk",
    version="1.1.0",
    author="ForensicSuite Team",
    description="Modulárna analytická platforma pre softvérové projekty – SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/forensicsuite",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Security",
    ],
    python_requires=">=3.9",
    install_requires=[
        # Žiadne externé závislosti – všetko je v štandardnej knižnici
    ],
    entry_points={
        "console_scripts": [
            "forensicsuite=cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
