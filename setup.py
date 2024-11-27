import os
from setuptools import setup, find_packages

subpackages = find_packages("solver_rewards")
packages = ["solver_rewards"] + ["solver_rewards." + p for p in subpackages]


def read_requirements(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def get_files(directory: str, extension: str):
    found_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                found_files.append(
                    os.path.join(
                        "solver_rewards", os.path.relpath(os.path.join(root, file), start="solver_rewards")
                    )
                )
    return found_files


setup(
    name="solver_rewards",
    version="1.6.4",
    packages=packages,
    package_dir={"solver_rewards": "solver_rewards"},
    include_package_data=True,
    data_files=[
        (
            os.path.join(
                "lib", "python{0}.{1}".format(*os.sys.version_info[:2]), "site-packages"
            ),
            ["logging.conf"],
        ),
        (
            os.path.join(
                "lib",
                "python{0}.{1}".format(*os.sys.version_info[:2]),
                "site-packages",
                "solver_rewards",
                "sql",
            ),
            get_files("solver_rewards/sql", ".sql"),
        ),
        (
            os.path.join(
                "lib",
                "python{0}.{1}".format(*os.sys.version_info[:2]),
                "site-packages",
                "solver_rewards",
                "abis",
            ),
            get_files("solver_rewards/abis", ".json"),
        ),
    ],
    install_requires=read_requirements("requirements.txt"),
)
