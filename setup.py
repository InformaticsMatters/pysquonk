import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="im-pysquonk",
    version="1.0.0",
    author="Malcolm Peacock",
    author_email="malcolm@popmalc.org.uk",
    description="Pysquonk rest server API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/InformaticsMatters/pysquonk",
    packages=setuptools.find_packages(exclude=['*.test', '*.test.*', 'test.*', 'test']),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)

