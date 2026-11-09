#!/usr/bin/env python3

"""本プログラムにおけるエラーの種類（入力・出力・モデル・生成）を定義する
"""

class CallMeMaybeError(Exception):
    """本プログラムの全例外の基底。"""
    ...

class InputFileError(CallMeMaybeError):
    """入力に関するエラー。

    - 入力ファイルが存在しない。
    - 入力ファイルの形式が JSON として不正、またはスキーマに合わない。
    """
    ...

class OutputFileError(CallMeMaybeError):
    """出力に関するエラー。

    - 出力ファイルに結果を書き込めない。
    """
    ...

class ModelError(CallMeMaybeError):
    """LLM に関するエラー。

    - llm_sdk が読み込む LLM（Qwen/Qwen3-0.6B）の読み込みに失敗した。
    - llm_sdk が返す語彙ファイル（vocab.json）の読み込みに失敗した。
    """
    ...

class DecodingError(CallMeMaybeError):
    """デコーディングに関するエラー。

    - 生成中に許可トークンが 1 つもなくなった。
    - 引数の値が最後まで完成しなかった。
    """
    ...
