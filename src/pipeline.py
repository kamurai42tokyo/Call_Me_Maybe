#!/usr/bin/env python3

"""このプログラムの処理の流れを順番に実行する

①入力ファイルの読込
　- 関数定義の読込： load_function_definitions で関数定義ファイルを読み込み、
　  　　　　　　　　 FunctionDefinition 型のリストを作る
　- 設問の読込    ： load_prompts で設問ファイルを読み込み、PromptItem 型のリストを作る
　- 読込失敗時    ： ファイルが無い・JSON が壊れている・形が合わない場合は
　  　　　　　　　　 InputFileError を送出

②LLMモデル（Small_LLM_Model）と語彙ファイル（vocab.json）の初期化
　- モデルの準備  ： Small_LLM_Model を作成し、LLM（Qwen/Qwen3-0.6B）を読み込む
　- 語彙の準備    ： get_path_to_vocab_file で得た vocab.json から Vocab を作成する
　- 担当の準備    ： モデル・語彙・関数定義リストを渡して、
　  　　　　　　　　 FunctionSelector と ConstrainedDecoder を作成
　- 読込失敗時    ： モデルや語彙ファイルを読み込めない場合は ModelError を送出

③設問ごとの関数選択・引数生成を実施し、出力データを作成
　- 設問の読み込み： PromptItem 型のデータを１件読込
　- 関数選択      ： FunctionSelector.select で関数（FunctionDefinition型）を１つ選ぶ
　- 引数生成      ： ConstrainedDecoder.generate_arguments で LLM に引数の値を作らせる
　- 出力データ    ： FunctionCall 型のインスタンスを作成

④保存
　- FunctionCall のリストを save_function_calls で出力ファイルに保存

"""

class Pipeline:
    def __init__(
            self, functions_definition: str, input: str, output: str) -> None:
        self.functions_definition: str = functions_definition
        self.input: str = input
        self.output: str = output
    
