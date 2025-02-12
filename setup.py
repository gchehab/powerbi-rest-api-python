import setuptools

setuptools.setup(
    name = "pbirest",
    packages = setuptools.find_packages(),
    version = "0.0.7",
    license = "MIT",
    description = "A Python library created to easily use the Power BI REST API with Python",
    long_description = "A Python library created to easily use the Power BI REST API with Python",
    author = "Antoine DE WILDE",
    author_email = "antoinedewilde7@gmail.com",
    url = "https://github.com/AntoineDW/powerbi-rest-api-python",
    keywords = ["power bi", "powerbi", "rest", "api", "rest api"],
    install_requires = [
        "requests"
    ],
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6"
    ]
)