from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="metadata-py",
    version="1.0.0",
    author="we256681",
    author_email="we256681@gmail.com",
    description="Утилита для управления метаданными в markdown-файлах с автоматическим контролем версий и определением автора",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/woodg9461/metadata-py",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "packaging>=20.0"
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Documentation",
        "Topic :: Text Processing :: Markup",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "metadata-py=update_metadata.cli:main",
        ],
    },
    include_package_data=True,
    package_data={"update_metadata": ["templates/*"]},
)