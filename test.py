#!/usr/bin/env python

import argparse
import os
import sys
import subprocess

BASE_URL = "https://github.com/kellegous/codeowner-test/"


def must_call(cmd: list):
    status = subprocess.call(cmd)
    if status != 0:
        raise Exception("Failed to run command: {}".format(cmd))


def touch_file(path: str):
    dir = os.path.dirname(path)
    if dir != "" and not os.path.exists(dir):
        os.makedirs(dir)
    with open(path, "w") as f:
        f.write("")


class Branch(object):
    def __init__(self, name: str, owners: list, files: dict):
        self.name = name
        self.owners = owners
        self.files = files.keys()

    def update(self) -> bool:
        self.delete()

        must_call(["git", "checkout", "-b", self.name])

        for file in self.files:
            touch_file(file)
            must_call(["git", "add", file])

        with open(".github/CODEOWNERS", "w") as f:
            for owner in self.owners:
                f.write("{}\n".format(owner))

        must_call(["git", "add", ".github/CODEOWNERS"])

        must_call(["git", "commit", "-m", "Update for : {}".format(self.name)])

        must_call(["git", "push", "origin", self.name])

    def delete(self) -> bool:
        a = subprocess.call(["git", "push", "origin", "--delete", self.name]) == 0
        b = subprocess.call(["git", "branch", "-D", self.name]) == 0
        return a and b


def update_readme():
    must_call(["git", "checkout", "main"])

    items = [
        "- [{}]({}tree/{})".format(branch.name, BASE_URL, branch.name)
        for branch in get_branches()
    ]

    with open("README.md", "w") as f:
        f.write("# Codeowner Test\n\n")
        f.write("## Branches\n\n")
        f.write("\n".join(items))
        f.write("\n")

    must_call(["git", "add", "README.md"])
    must_call(["git", "commit", "-m", "Update README.md"])
    must_call(["git", "push"])


def create_test(args):
    branches = select_branches(args.names)
    must_call(["git", "checkout", "main"])
    for branch in branches:
        branch.update()
    update_readme()


def delete_test(args):
    branches = select_branches([args.name])
    must_call(["git", "checkout", "main"])
    for branch in branches:
        if not branch.delete():
            raise Exception("Failed to delete branch: {}".format(branch.name))
    update_readme()


def select_branches(names: list) -> list:
    if len(names) == 0:
        return get_branches()

    by_name = {b.name: b for b in get_branches()}

    def find_branch(name: str) -> Branch:
        branch = by_name.get(name)
        if branch is None:
            raise Exception("Branch not found: {}".format(name))
        return branch

    return [find_branch(name) for name in names]


def get_branches():
    return [
        Branch(
            "example-a",
            ["* @kellegous"],
            {
                "a": 1,
                "b/a": 1,
                "c/b/a": 1,
            },
        ),  # ok
        Branch(
            "example-b",
            ["*.js @kellegous"],
            {
                "a.js": 1,
                "b/a.js": 1,
                "c.js/b": 1,
            },
        ),  # ok
        Branch(
            "example-c",
            ["/a/logs/ @kellegous", "/b/logs/ @kellegous"],
            {
                "a/logs": None,
                "b/logs/a": 2,
                "b/logs/c/a": 2,
            },
        ),  # ok
        Branch(
            "example-d",
            ["a/* @kellegous", "b/* @kellegous"],
            {
                "a": None,
                "b/a.txt": 2,
                "b/c/a.txt": None,
                "x/b/a.txt": None,
            },
        ),  # ok
        Branch(
            "example-e",
            ["a/ @kellegous", "b/ @kellegous"],
            {
                "a": None,
                "b/a.txt": 2,
                "b/c/a.txt": 2,
                "x/b/a.txt": 2,  # surprise
            },
        ),  # ok
        Branch(
            "example-f",
            ["/a/ @kellegous", "/b/ @kellegous"],
            {
                "a": None,
                "b/a.txt": 2,
                "b/c/a.txt": 2,
                "x/b/a.txt": None,
            },  # ok
        ),
        Branch(
            "example-g",
            ["**/a @kellegous", "**/b @kellegous"],
            {
                "a": 1,
                "b/c": 2,
                "b/a": 2,
                "b/d/e": 2,
                "c/d/a": 1,
            },  # ok
        ),
        Branch(
            "example-h",
            ["a/** @kellegous", "b/** @kellegous"],
            {
                "a": None,
                "b/a.txt": 2,
                "b/c/a.txt": 2,
                "x/b/a.txt": None,
            },
        ),  # ok
        Branch(
            "example-i",
            ["a/**/b @kellegous"],
            {
                "a/b": 1,
                "a/x/b": 1,
                "a/y/b/c": 1,
                "x/a/b": None,
                "x/a/x/b": None,
            },
        ),  # ok
    ]


def main():
    parser = argparse.ArgumentParser(prog="test.py")
    sub_parsers = parser.add_subparsers(help="subcommand help", required=True)

    create = sub_parsers.add_parser("create", help="create help")
    create.add_argument("names", nargs="*", default=[], help="name help")
    create.set_defaults(func=create_test)

    delete = sub_parsers.add_parser("delete", help="delete help")
    delete.add_argument("name", help="name help")
    delete.set_defaults(func=delete_test)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
