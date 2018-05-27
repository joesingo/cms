from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f.readlines()]

setup(
    name="mdss",
    version="0.0.1",
    description="Build static websites with jinja2 templates and markdown",
    install_requires=requirements,
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "mdss=mdss.gen_site:main"
        ]
    }
)
