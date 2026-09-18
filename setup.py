import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), "README.md")) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="openimis-be-pwp_api",
    version="0.1.0",
    packages=find_packages(include=["pwp_api", "pwp_api.*"]),
    include_package_data=True,
    license="GNU AGPL v3",
    description="Reusable openIMIS PWP API module infrastructure.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/nlgfc2024/openimis-be-pwp_api_py",
    author="Faris Ahmetasevic",
    author_email="faris.ahmetasevic@hotmail.com",
    python_requires=">=3.10",
    install_requires=[
        "django>=4.2,<5.0",
        "djangorestframework>=3.14,<4",
        "drf-spectacular>=0.25,<1",
        "aiohttp>=3.13.3,<4",
        "openimis-be-core>=1.11,<2",
        "django-simple-history>=3.8,<4",
        "django-dirtyfields>=1.4,<2",
    ],
    classifiers=[
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
)
