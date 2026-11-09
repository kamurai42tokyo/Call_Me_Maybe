#!/usr/bin/env python3

"""入力ファイル及び出力ファイルのデータ型を定義し、形が合わないデータを拒否する。
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class ParameterSpec(BaseModel):
    """入力ファイル（data/input/functions_definition.json）における引数１つまたは戻り値の型。"""

    model_config = ConfigDict(extra="forbid")

    type: Literal["number", "integer", "string", "boolean"]


class FunctionDefinition(BaseModel):
    """入力ファイル（data/input/functions_definition.json）の要素 1 件。"""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    parameters: dict[str, ParameterSpec]
    returns: ParameterSpec


class PromptItem(BaseModel):
    """入力ファイル（data/input/function_calling_tests.json）の要素 1 件。"""

    model_config = ConfigDict(extra="forbid")

    prompt: str


class FunctionCall(BaseModel):
    """出力ファイル（data/output/function_calling_results.json）の要素 1 件。"""

    model_config = ConfigDict(extra="forbid")

    prompt: str
    name: str
    parameters: dict[str, float | int | str | bool]
