#!/usr/bin/env python3

"""プログラム全体の処理（読込 → モデル準備 → 関数選択・引数生成 → 保存）を順に実行する。

①入力ファイルの読込
　- 関数定義の読込： load_function_definitions() で関数定義ファイルを読み込み、
　  　　　　　　　　 FunctionDefinition 型のリストを作る
　- 設問の読込    ： load_prompts() で設問ファイルを読み込み、Prompt 型のリストを作る
　- 読込失敗時    ： ファイルが無い・JSON が壊れている・形が合わない場合は
　  　　　　　　　　 InputFileError を送出

②LLMモデル（Small_LLM_Model）と語彙ファイル（vocab.json）の初期化
　- モデルの準備  ： Small_LLM_Model インスタンスを作成し、LLM（Qwen/Qwen3-0.6B）を読み込む
　- 語彙の準備    ： Small_LLM_Model.get_path_to_vocab_file() で得た vocab.json から
　  　　　　　       Vocab を作成する
　- 担当の準備    ： モデル・語彙・関数定義リストを渡して、
　  　　　　　　　　 FunctionSelector インスタンスと ConstrainedDecoder インスタンスを作成
　- 読込失敗時    ： モデルや語彙ファイルを読み込めない場合は ModelError を送出

③設問ごとの関数選択・引数生成を実施し、出力データを作成
　- 設問の読み込み： Prompt 型のデータを１件読込
　- 関数選択      ： FunctionSelector.select() で関数（FunctionDefinition型）を１つ選ぶ
　- 引数生成      ： ConstrainedDecoder.generate_arguments() で LLM に引数の値を作らせる
　- 出力データ    ： FunctionCall 型のインスタンスを作成

④保存
　- FunctionCall のリストを save_function_calls() で出力ファイルに保存

"""

from .io_utils import (
    load_function_definitions, load_prompts, save_function_calls)
from .models import FunctionDefinition, Prompt, FunctionCall
from .vocab import Vocab
from .selector import FunctionSelector
from .decoder import ConstrainedDecoder
from .errors import ModelError
from llm_sdk import Small_LLM_Model


class Pipeline:
    """入力の読込から結果の保存までの処理を、順番に実行する。"""

    def __init__(
            self,
            functions_definition_path: str,
            prompts_path: str,
            output_path: str
            ) -> None:
        """入出力ファイルのパスを受け取って保持する。

        Args:
            functions_definition_path: 関数定義ファイルのパス。
            prompts_path: 設問ファイルのパス。
            output_path: 結果を保存するファイルのパス。
        """
        self.functions_definition_path: str = functions_definition_path
        self.prompts_path: str = prompts_path
        self.output_path: str = output_path

    def run(self) -> None:
        """入力の読込・モデルの準備・関数選択と引数生成・保存を順に実行する。

        Raises:
            InputFileError: 入力ファイルが読めない、または形式が不正な場合。
            ModelError: モデルまたは語彙ファイルを読み込めない場合。
            OutputFileError: 結果ファイルに書き込めない場合。
        """

        # 関数定義ファイルの読込
        function_definitions: list[FunctionDefinition] = \
            load_function_definitions(self.functions_definition_path)

        # プロンプトファイルの読込
        prompts: list[Prompt] = load_prompts(self.prompts_path)

        # LLMモデルのインポートと語彙ファイルのパスの確保
        try:
            model = Small_LLM_Model()
            vocab_path: str = model.get_path_to_vocab_file()
            vocab = Vocab(vocab_path)
        except Exception as e:
            raise ModelError(f"Failed to load model: {e}")

        # “設問１件に対して、呼ぶべき関数を１つ選ぶ” 役割を担うインスタンスの作成
        function_selector = FunctionSelector(model, function_definitions)

        # “選ばれた関数の引数の値を、型に合う形でLLMに作らせる” 役割を担うインスタンスの作成
        constrained_decoder = ConstrainedDecoder(
            model, vocab, function_selector.text_header)

        # 出力する内容をひとまとめにするリスト
        function_calls: list[FunctionCall] = []

        # 設問ごとの関数選択・引数生成を実施 → 出力データを作成
        for i, prompt in enumerate(prompts, 1):
            selected_function: FunctionDefinition = \
                function_selector.select(prompt)
            arguments: dict[str, float | int | str | bool] = \
                constrained_decoder.generate_arguments(
                    prompt, selected_function)
            function_call = FunctionCall(
                prompt=prompt.prompt,
                name=selected_function.name,
                parameters=arguments
            )
            function_calls.append(function_call)
            print(
                f"[{i}/{len(prompts)}] {function_call.prompt} -> "
                f"{function_call.name} {function_call.parameters}",
                flush=True
                )

        # 出力内容を出力ファイルへ保存する（未作成の場合は新規に作成する）
        save_function_calls(self.output_path, function_calls)
