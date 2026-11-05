#!/usr/bin/env python3

""" このプログラムの目的：
        「設問」を「関数名」と「引数」を持つ JSON に変換する。

    入力：
        ① 「設問」を記載した JSON ファイル（input/function_calling_tests.json）
            例）"What is the sum of 2 and 3?"
        ② 「関数名」を記載した JSON ファイル（input/functions_definition.json）
            例）"fn_add_numbers"
    
    処理：
        入力①に記載している各「設問」に対して、入力②から適切な「関数名」と、
        渡すべき「引数」を判定して、出力するための JSON としてまとめる。
    
    出力：
        「設問」「関数名」「引数」を持つ JSON（標準出力）
            例）{"prompt":"Is 4 an even number?","name":"fn_is_even","parameters":{"n":4}}
"""

from errors import ArgumentError
import sys, tools


def main(argv: list[str]) -> int:
    """ このプログラムの中枢 """
    
    # 引数の数や形式が間違っていないかを検証する。
    try:
        tools.check_arg()
    except ArgumentError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
