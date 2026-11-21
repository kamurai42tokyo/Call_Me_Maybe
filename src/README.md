このプログラムの目的：
        「設問」を「関数名」と「引数」を持つ JSON に変換する。

    入力：
        ① 「設問」を記載した JSON ファイル（data/input/function_calling_tests.json）
            例）"What is the sum of 2 and 3?"
        ② 「関数名」を記載した JSON ファイル（data/input/functions_definition.json）
            例）"fn_add_numbers"
    
    処理：
        入力①に記載している各「設問」に対して、入力②から適切な「関数名」と、
        渡すべき「引数」を判定して、出力するための JSON としてまとめる。

    判定方法：
        ① 関数名の判定（FunctionSelector.select()）
            - 「設問」から「モデルに渡す文章」（"Question: <設問>\nFunction name: "）を作る。
            - 入力②の各「関数名」について、その関数名が「モデルに渡す文章」の
              続きとして来る確率を LLM で求める。
                - 関数名はいくつかのトークン（単語のかけら）に分かれるため、
                  各トークンが直前の文章の次に来る確率を softmax で求め、
                  その log（対数確率）を足し合わせて score とする。
                - score は「その関数名が次に来る確率の log」になる。
            - score が最も高い関数を、呼び出す関数として選ぶ。
              （LLM に自由に書かせず、候補の中から選ばせるため、
                存在しない関数名が出力されることはない）

        ② 引数の判定（ConstrainedDecoder.generate_arguments()）
            - ①で選んだ関数の引数ごとに、「設問」・関数名・引数名を並べた文章を作り、
              LLM に引数の値を 1 トークンずつ生成させる。
            - 各トークンを選ぶとき、引数の型（number / integer / string / boolean）に
              合わないトークンは候補から外し、残った中で最も点数の高いトークンを選ぶ
              （制約付きデコーディング）。
                例）number 型なら、数字・"-"・"." だけを候補にする。
            - 生成した値を引数の型に変換し、「引数」としてまとめる。
    
    出力：
        「設問」「関数名」「引数」を持つ JSON（data/output/~~~.json）
            例）{"prompt":"Is 4 an even number?","name":"fn_is_even","parameters":{"n":4}}

    ファイルの読み書き（src/io_utils.py）：
        JSON ファイルの読み書きには、Python 標準の json モジュールを使う。
        ファイルは with open(...) で開き、使い終わったら自動で閉じる。

        - json.load(f)
            JSON ファイルを読み込み、Python のデータ（dict / list）に変換する。
            （load_function_definitions()、load_prompts() で使う）
        - json.dump(data, f)
            Python のデータを JSON に変換し、ファイルに書き込む。
            （save_function_calls() で使う）

        - 入力ファイルが存在しない場合（FileNotFoundError）や、
          JSON として正しくない場合（json.JSONDecodeError）はエラーとして扱う。


    実行方法：
        下記のコマンドで実行する。

        uv run python -m src
        --functions_definition data/input/functions_definition.json
        --input data/input/function_calling_tests.json
        --output data/output/function_calls.json

    