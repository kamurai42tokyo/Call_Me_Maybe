#!/usr/bin/env python3

"""自然言語の「設問」を、呼び出す関数名と引数を持つ JSON に変換する。

使い方:
    uv run python -m src [--functions_definition <file>]
                         [--input <file>] [--output <file>]

入力:
    1. 設問ファイル（既定: data/input/function_calling_tests.json）
       例) [{"prompt": "What is the sum of 2 and 3?"}, ...]
    2. 関数定義ファイル（既定: data/input/functions_definition.json）
       関数名・引数の名前と型・戻り値の型・説明を持つ関数のリスト。
       例) [{"name": "fn_add_numbers", "parameters": {...}, ...}, ...]

処理:
    各設問について、関数定義の中から呼び出すべき関数を LLM で選び、
    その関数の引数を制約付きデコーディングで生成する。

出力:
    設問・関数名・引数を持つオブジェクトの JSON 配列をファイルに書き出す。
    （既定: data/output/function_calling_results.json）
    例) [{"prompt": "What is the sum of 2 and 3?",
          "name": "fn_add_numbers",
          "parameters": {"a": 2.0, "b": 3.0}}, ...]

終了コード:
    0: 正常終了
    1: 入出力・モデル・デコーディングのいずれかでエラーが発生した
"""

from .pipeline import Pipeline
from .errors import CallMeMaybeError
import sys
import argparse


def main(argv: list[str]) -> int:
    """コマンドライン引数を解析し、Pipeline を実行する。

    Args:
        argv: コマンドライン引数（sys.argv をそのまま渡す）。

    Returns:
        終了コード。正常終了なら 0、エラー時は 1。
    """

    # コマンドライン引数（入出力ファイルのパス）を解析して args に入れる
    # argparse.ArgumentParser() : 解析係（parser）の作成
    # add_argument(...)         : 受け付けるオプションと、それぞれの既定値の登録
    # parse_args(argv[1:])      : 実際のコマンドライン引数を読んで、各パスを args にまとめる
    parser = argparse.ArgumentParser()
    parser.add_argument("--functions_definition",
                        default="data/input/functions_definition.json")
    parser.add_argument("--input",
                        default="data/input/function_calling_tests.json")
    parser.add_argument("--output",
                        default="data/output/function_calling_results.json")
    args: argparse.Namespace = parser.parse_args(argv[1:])

    # args を引数として Pipeline に渡して実行する。
    try:
        Pipeline(args.functions_definition, args.input, args.output).run()
    except CallMeMaybeError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
