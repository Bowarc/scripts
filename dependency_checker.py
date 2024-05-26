""".
    

    global dependency: the ones in root/cargo.toml

    conflict: a global dependecy that is also imported specificly by a package

    This script ensure that:
        Every dependecy used by 2 or more packages are a global dependencies
        There is not unused global dependencies
        Every dependecy of every package is used at least one time

    Requirements:
        rg (https://github.com/BurntSushi/ripgrep)

    Author: Bowarc
"""

import os
from threading import Thread
import subprocess


class Dependencies:
    def __init__(self, package):
        self.package = package
        self.specifics = []
        self.globals = []

        self.fetch()

    def __str__(self):
        if self.package == ".":
            return "root"
        return self.package

    def add_specific(self, dep_name):
        self.specifics.append(dep_name)

    def add_global(self, dep_name):
        self.globals.append(dep_name)

    def get_specifics(self):
        return self.specifics

    def get_globals(self):
        return self.globals

    def get_all(self):
        return self.specifics + self.globals

    def fetch(self):
        cargo_toml = f"{self.package}/cargo.toml"

        with open(cargo_toml, "r") as f:
            found_dependencies = False

            for line in f:
                line = line.replace(" ", "").replace("\n", "")
                if line == "":
                    continue

                if line.startswith("["):
                    if line.endswith("dependencies]"):
                        found_dependencies = True
                    else:
                        found_dependencies = False
                    continue

                if line.startswith("#"):
                    continue

                if not found_dependencies:
                    continue

                raw_dep_name = line.split(".")[0].split("=")[0]

                # if raw_dep_name == "shared":
                # continue

                if ".workspace=true" in line:
                    self.add_global(raw_dep_name)
                else:
                    self.add_specific(raw_dep_name)

    def check_unused(self):
        import threading

        threads = []
        results = {}

        for dep in self.get_all():
            results[dep] = None
            t = threading.Thread(
                target=check_unused_thread_fn, args=(dep, self.package, results)
            )
            t.start()

            threads.append(t)

        return threads, results


def check_unused_thread_fn(dep, package, results):
    dep_ = dep.replace("-", "_")

    s1 = f"{dep_}::"
    s2 = f"use {dep_}"
    s3 = f"extern crate {dep_}"

    proc = subprocess.Popen(
        f'rg "{s1}|{s2}|{s3}" {package}/src/', stdout=subprocess.PIPE
    ).communicate()[0]

    # print(proc)

    if proc != b"":
        results[dep] = True
        return
    results[dep] = False


def fetch_packages() -> [str]:
    packages = []
    for item in os.listdir(".") + ["."]:
        if not os.path.isdir(os.path.join(".", item)):
            continue

        is_package = False
        for inner in os.listdir(item):
            if not os.path.isfile(os.path.join(item, inner)):
                continue

            if inner.lower() != "cargo.toml":
                continue
            is_package = True

            break
        if not is_package:
            continue

        packages.append(item)
    return packages


def check_globals(package_dependencies):
    # Checks for unused global dependecy
    threshold = 1

    global_deps = []
    specific_deps = []
    for package in package_dependencies:
        if package.package == ".":
            global_deps += package.get_specifics()
        else:
            specific_deps += package.get_globals()

    # print(global_deps, specific_deps)
    unused = []

    for gdep in global_deps:
        count = 0
        for sdep in specific_deps:
            if gdep == sdep:
                count += 1
        if count < threshold:
            unused.append(gdep)

    if len(unused) != 0:
        print(
            f"The global dependecies {unused} are used less than {threshold} package{'s'if threshold > 1 else ''}".replace(
                "'", ""
            )
        )
    else:
        print(
            f"Every global dependecy is used at least {threshold} time{'s'if threshold > 1 else ''}"
        )


def find_conflicts(package_dependencies):
    # conflicts = 0

    for i, dep1 in enumerate(package_dependencies):
        for j in range(i + 1, len(package_dependencies)):
            dep2 = package_dependencies[j]
            # print(f"Testing {dep1.package} against {dep2.package}")
            for d in dep1.get_specifics():
                if d in dep2.get_specifics():
                    print(f"Conlict of {d} in {dep1}-{dep2}")
                    # conflicts += 1

    # print(f"Found {conflicts} conflicts")


def check_unused(package_dependencies):
    # Check if a dependency imported by a package is used

    threads = []
    results = {}

    for package_dep in package_dependencies:
        if package_dep.package == ".":
            continue
        t, r = package_dep.check_unused()

        threads += t

        results[package_dep.package] = r

    for thread in threads:
        thread.join()

    for i, (package, r) in enumerate(results.items()):
        # Here we keep only entries where the result is not True (True means the dependency is used)
        r = {key: val for key, val in r.items() if val != True}
        if len(r) == 0:
            continue
        print()
        for dep, used in r.items():
            if used == True:
                # print("Should not be happening")
                continue
            if used == None:
                print(
                    f"Diddn't receive any information about the dependency {dep} in {package}, this means that the thread has crashed"
                )
                continue
            print(f"Unused dep in {package}: {dep}")


def main():

    # Get all packages
    packages = fetch_packages()
    print(packages, "\n")

    # Find all their dependencies
    package_dependencies = [Dependencies(package) for package in packages]

    # Make sure that every global dep is used by a package
    check_globals(package_dependencies)
    print()

    # Check if there are any conflict
    find_conflicts(package_dependencies)

    # Check if they are all used
    check_unused(package_dependencies),


if __name__ == "__main__":
    main()
