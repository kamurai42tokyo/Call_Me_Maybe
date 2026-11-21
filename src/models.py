#!/usr/bin/env python3

"""入力ファイルと出力ファイルのデータの形を pydantic で定義する。

形が合わないデータは、読み込み時に ValidationError として拒否される。
ParameterSpec / FunctionDefinition / Prompt: 入力ファイルの要素。
FunctionCall: 出力ファイルの要素。
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class ParameterSpec(BaseModel):
    """関数定義ファイルで、引数 1 つまたは戻り値の型を表す。

    data/input/functions_definition.json の {"type": "number"} の部分にあたる。

    Attributes:
        type: 値の型。"number"（小数）, "integer"（整数）,
            "string"（文字列）, "boolean"（真偽値）のどれか。
    """

    model_config = ConfigDict(extra="ignore")

    type: Literal["number", "integer", "string", "boolean"]


class FunctionDefinition(BaseModel):
    """関数定義ファイル（data/input/functions_definition.json）の要素 1 件。

    Attributes:
        name: 関数名（例: "fn_add_numbers"）。
        description: 関数が何をするかの説明文（現状、関数選択には使っていない）。
        parameters: 引数名をキー、その型を値にした辞書（例: {"a": ParameterSpec}）。
        returns: 戻り値の型。
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    description: str
    parameters: dict[str, ParameterSpec]
    returns: ParameterSpec


class Prompt(BaseModel):
    """設問ファイル（data/input/function_calling_tests.json）の要素 1 件。

    Attributes:
        prompt: 自然文の設問（例: "What is the sum of 2 and 3?"）。
    """

    model_config = ConfigDict(extra="ignore")

    prompt: str


class FunctionCall(BaseModel):
    """出力ファイル（data/output/function_calling_results.json）の要素 1 件。

    Attributes:
        prompt: 元になった設問の文。
        name: 選ばれた関数名。
        parameters: 引数名をキー、生成した値を値にした辞書（例: {"a": 2.0, "b": 3.0}）。
    """

    model_config = ConfigDict(extra="forbid")

    prompt: str
    name: str
    parameters: dict[str, float | int | str | bool]
