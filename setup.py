import os
from setuptools import setup, find_packages

subpackages = find_packages("src")
packages = ["src"] + ["src." + p for p in subpackages]


def read_requirements(filename):
    with open(filename, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def get_sql_files(directory):
    sql_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".sql"):
                # Add 'src/' prefix to the path
                sql_files.append(
                    os.path.join(
                        "src", os.path.relpath(os.path.join(root, file), start="src")
                    )
                )
    return sql_files


setup(
    name="solver-rewards",
    version="1.6.4",
    packages=packages,
    package_dir={"": "src"},
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
            get_sql_files("queries"),
        ),
    ],
    install_requires=read_requirements("requirements/prod.txt"),
)
