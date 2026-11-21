#!/usr/bin/env python3

"""本プログラムで使う例外の種類を定義する。

CallMeMaybeError を基底とし、入力（InputFileError）・出力（OutputFileError）・
モデル（ModelError）の 3 種類に分ける。
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
