#!/usr/bin/env python3

"""入力ファイルの読み込みと、結果ファイルへの保存を行う。

load_function_definitions: 関数定義ファイルを読み込む。
load_prompts: 設問ファイルを読み込む。
save_function_calls: 判定結果を JSON ファイルに保存する。
"""

from .models import FunctionDefinition, Prompt, FunctionCall
from .errors import InputFileError, OutputFileError
from pydantic import ValidationError
from typing import Any
from pathlib import Path
import json


def load_function_definitions(
        functions_definition_path: str) -> list[FunctionDefinition]:
    """関数定義ファイルを読み込み、FunctionDefinition のリストにして返す。

    data/input/functions_definition.json を json.load で読み込み、
    要素 1 件ずつを FunctionDefinition に変換する。

    Args:
        functions_definition_path: 関数定義ファイルのパス。

    Returns:
        関数定義のリスト。

    Raises:
        InputFileError: ファイルが読めない、JSON が不正、
            または形式が合わない場合。
    """
    # 関数定義ファイルを読み込む。
    try:
        with open(functions_definition_path, "r", encoding="utf-8") as f:
            data: list[dict[str, Any]] = json.load(f)
        if not isinstance(data, list):
            raise InputFileError(
                f"Expected a JSON array in {functions_definition_path}, "
                f"got {type(data).__name__}")
    except FileNotFoundError:
        raise InputFileError(f"File not found: {functions_definition_path}")
    except OSError as e:
        raise InputFileError(
            f"Cannot read file: {functions_definition_path}: {e}")
    except UnicodeDecodeError as e:
        raise InputFileError(
            f"File is not UTF-8: {functions_definition_path}: {e}")
    except json.JSONDecodeError as e:
        raise InputFileError(
            f"Invalid JSON in {functions_definition_path}: {e}")

    # 読み込んだ関数定義をひとまとめにするリスト
    function_definitions: list[FunctionDefinition] = []

    # 要素 1 件ずつを FunctionDefinition 型に変換 → 返り値を作成
    for item in data:
        try:
            function_definition = FunctionDefinition.model_validate(item)
            function_definitions.append(function_definition)
        except ValidationError as e:
            raise InputFileError(
                f"Invalid function definition in "
                f"{functions_definition_path}: {e}")

    # 関数定義が空の場合はエラー
    if not function_definitions:
        raise InputFileError(
            f"No function definitions in {functions_definition_path}")

    # 読み込んだ FunctionDefinition のリストを返す。
    return function_definitions


def load_prompts(prompts_path: str) -> list[Prompt]:
    """設問ファイルを読み込み、Prompt のリストにして返す。

    data/input/function_calling_tests.json を json.load で読み込み、
    要素 1 件ずつを Prompt に変換する。

    Args:
        prompts_path: 設問ファイルのパス。

    Returns:
        設問のリスト。

    Raises:
        InputFileError: ファイルが読めない、JSON が不正、
            または形式が合わない場合。
    """
    # 設問ファイルを読み込む。
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            data: list[dict[str, Any]] = json.load(f)
        if not isinstance(data, list):
            raise InputFileError(
                f"Expected a JSON array in {prompts_path}, "
                f"got {type(data).__name__}")
    except FileNotFoundError:
        raise InputFileError(f"File not found: {prompts_path}")
    except OSError as e:
        raise InputFileError(f"Cannot read file: {prompts_path}: {e}")
    except UnicodeDecodeError as e:
        raise InputFileError(f"File is not UTF-8: {prompts_path}: {e}")
    except json.JSONDecodeError as e:
        raise InputFileError(f"Invalid JSON in {prompts_path}: {e}")

    # 読み込んだ設問をひとまとめにするリスト
    prompts: list[Prompt] = []

    # 要素 1 件ずつを Prompt 型に変換 → 返り値を作成
    for item in data:
        try:
            prompt = Prompt.model_validate(item)
            prompts.append(prompt)
        except ValidationError as e:
            raise InputFileError(f"Invalid prompt in {prompts_path}: {e}")

    # 読み込んだ Prompt のリストを返す。
    return prompts


def save_function_calls(
        output_path: str, function_calls: list[FunctionCall]) -> None:
    """判定結果のリストを JSON ファイルに保存する。

    各 FunctionCall を辞書に変換し、json.dump で output_path に書き込む。

    Args:
        output_path: 保存先ファイルのパス（例: data/output/function_calls.json）。
        function_calls: 保存する判定結果（設問・関数名・引数）のリスト。

    Raises:
        OutputFileError: 出力ファイルに書き込めない場合。
    """
    # FunctionCall 型を、json.dump がJSONに変換可能な型に変える。
    data: list[dict[str, Any]] = \
        [function_call.model_dump() for function_call in function_calls]

    # 判定結果を保存先のファイルパスへ保存する。
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except TypeError as e:
        raise OutputFileError(
            f"Failed to convert results to JSON: {output_path}: {e}")
    except OSError as e:
        raise OutputFileError(
            f"Failed to write output file: {output_path}: {e}")
