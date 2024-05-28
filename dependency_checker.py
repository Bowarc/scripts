""".
    Global dependency: the ones in root/cargo.toml

    Conflict: a global dependency that is also imported specifically by a package

    This script ensure that:
        Every dependency used by 2 or more packages are a global dependencies
        There is no unused global dependencies
        Every dependency of every package is used at least once

    Requirements:
        rg (https://github.com/BurntSushi/ripgrep)

    Author: Bowarc
"""

import os
import subprocess
from typing import List, Tuple


class Dependencies:
    def __init__(self, package: str) -> None:
        self.package: str = package
        self.specifics: List[str] = []
        self.globals: List[str] = []

        self.fetch()

    def __str__(self) -> str:
        return "root" if self.package == "." else self.package

    def add_specific(self, dep_name: str) -> None:
        self.specifics.append(dep_name)

    def add_global(self, dep_name: str) -> None:
        self.globals.append(dep_name)

    def get_specifics(self) -> List[str]:
        return self.specifics

    def get_globals(self) -> List[str]:
        return self.globals

    def get_all(self) -> List[str]:
        return self.specifics + self.globals

    def fetch(self) -> None:
        cargo_toml: str = os.path.join(self.package, "cargo.toml")
        try:
            with open(cargo_toml, "r") as f:
                found_dependencies: bool = False

                for line in f:
                    line: str = line.replace(" ", "").replace("\n", "")
                    if not line:
                        continue

                    if line.startswith("["):
                        found_dependencies = line.endswith("dependencies]")
                        continue

                    if line.startswith("#") or not found_dependencies:
                        continue

                    raw_dep_name: str = line.split(".")[0].split("=")[0]
                    if ".workspace=true" in line:
                        self.add_global(raw_dep_name)
                    else:
                        self.add_specific(raw_dep_name)
        except FileNotFoundError:
            print(f"File {cargo_toml} not found.")
        except Exception as e:
            print(f"Error reading {cargo_toml}: {e}")


def fetch_packages() -> List[str]:
    packages: List[str] = []
    for item in os.listdir(".") + ["."]:
        if not os.path.isdir(os.path.join(".", item)):
            continue

        if any(inner.lower() == "cargo.toml" for inner in os.listdir(item) if os.path.isfile(os.path.join(item, inner))):
            packages.append(item)
    return packages


def check_globals(package_dependencies: List[Dependencies]) -> None:
    # Checks for unused global dependency
    global_deps: List[str] = []
    specific_deps: List[str] = []
    for package in package_dependencies:
        if package.package == ".":
            global_deps += package.get_specifics()
        else:
            specific_deps += package.get_globals()

    unused: List[str] = [gdep for gdep in global_deps if specific_deps.count(gdep) < 1]

    if unused:
        print(f"The global dependencies {unused} are used less than 1 package")
    else:
        print("Every global dependency is used at least once")


def find_conflicts(package_dependencies: List[Dependencies]) -> None:
    for i, dep1 in enumerate(package_dependencies):
        for j in range(i + 1, len(package_dependencies)):
            dep2: Dependencies = package_dependencies[j]
            for d in dep1.get_specifics():
                if d in dep2.get_specifics():
                    print(f"Conflict of {d} in {dep1}-{dep2}")


def check_unused(package_dependencies: List[Dependencies]) -> None:
    # Check if a dependency imported by a package is used

    processes: dict = {}

    for package_dep in package_dependencies:
        if package_dep.package == ".":
            continue

        results: List[Tuple[str, subprocess.Popen]] = []
        for dep in package_dep.get_all():
            r_dep: str = dep.replace("-", "_")

            pattern: str = f"{r_dep}::|use {r_dep}|extern crate {r_dep}"

            process: subprocess.Popen = subprocess.Popen(
                ["rg", pattern, os.path.join(package_dep.package, "src")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            results.append((dep, process))

        processes[package_dep.package] = results

    for package, results in processes.items():
        tag: bool = True
        # iter over results, build a list of dep which processes returned nothing (bat found no trace of the dep name in the code)
        for dep in {dep for dep, process in results if process.communicate()[0] == b''}:
            if tag:
                print()
                tag = False
            print(f"Unused dep in {package}: {dep}")


def main() -> None:

    # Get all packages
    packages: List[str] = fetch_packages()
    print(packages, "\n")

    # Find all their dependencies
    package_dependencies: List[Dependencies] = [Dependencies(package) for package in packages]

    # Make sure that every global dep is used by a package
    check_globals(package_dependencies)
    print()

    # Check if there are any conflicts
    find_conflicts(package_dependencies)

    # Check if they are all used
    check_unused(package_dependencies),


if __name__ == "__main__":
    main()
