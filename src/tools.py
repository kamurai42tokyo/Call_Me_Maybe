#!/usr/bin/env python3

from errors import ArgumentError


def check_arg(argv: list[str]) -> None:
    """ 引数の数や形式が間違っていないかを検証する。 """

    # 引数の数のチェック
    options: list[str] = ["--functions_definition", "--input", "--output"]
    arg_num: int = 0
    for arg in argv:
        if arg in options:
            arg_num += 1
    if not (len(argv) - arg_num * 2 == 1):
        raise ArgumentError("Invalid number of arguments")
    if not (len(argv) == len(set(argv))):
        raise ArgumentError("Duplicate argument")
