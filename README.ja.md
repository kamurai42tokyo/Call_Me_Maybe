*This project has been created as part of the 42 curriculum by kamurai.*

# call me maybe（日本語版）

> 課題の要件により、正式な README は英語版の [README.md](README.md) です。本書はその日本語版です。

## 概要（Description）

このプログラムは、自然文の「設問」を「関数名」と「引数」を持つ JSON に変換する。

- **入力①**：「設問」を記載した JSON ファイル（`data/input/function_calling_tests.json`）

  ```json
  [
    {
      "prompt": "What is the sum of 2 and 3?"
    },
    {
      "prompt": "Greet shrek"
    },
    ...
  ]
  ```

- **入力②**：「関数定義」を記載した JSON ファイル（`data/input/functions_definition.json`）

  ```json
  [
    {
      "name": "fn_add_numbers",
      "description": "Add two numbers together and return their sum.",
      "parameters": {
        "a": {
          "type": "number"
        },
        "b": {
          "type": "number"
        }
      },
      "returns": {
        "type": "number"
      }
    },
    ...
  ]
  ```

- **処理**：入力①の各「設問」に対して、LLM（Qwen/Qwen3-0.6B）を使って入力②から適切な関数を選ぶ。
  そのあと、渡すべき「引数」を制約付きデコーディングで生成する。
- **出力**：`prompt`・`name`・`parameters` を持つオブジェクトの JSON 配列（`data/output/function_calling_results.json`）

  ```json
  [
    {
      "prompt": "What is the sum of 2 and 3?",
      "name": "fn_add_numbers",
      "parameters": {
        "a": 2.0,
        "b": 3.0
      }
    },
    {
      "prompt": "Greet shrek",
      "name": "fn_greet",
      "parameters": {
        "name": "shrek"
      }
    },
    ...
  ]
  ```

## 実行準備と実行方法（Instructions）

### 必要なもの

- Python 3.10 以上
- [uv](https://docs.astral.sh/uv/)

### Makefile のルール

| ルール | 内容 |
| --- | --- |
| `make` / `make usage` | ルールの一覧を表示する |
| `make install` | 依存パッケージをインストールする（`uv sync`） |
| `make run` | プログラムを実行する（`uv run python -m src`） |
| `make debug` | `pdb` でプログラムを実行する |
| `make clean` | `__pycache__`・`.mypy_cache`・`.pytest_cache` を削除する |
| `make lint` | `flake8` と、指定のオプション付きの `mypy .` を実行する |
| `make lint-strict` | `flake8` と `mypy . --strict` を実行する |

`make install` で、numpy・pydantic・flake8・mypy と、同梱の `llm_sdk` パッケージ（`./llm_sdk`）がインストールされる。
モデル（Qwen/Qwen3-0.6B）は、初回の実行時に自動でダウンロードされる。

## 使用例（Example usage）

既定のパスで実行する場合：

    uv run python -m src

パスを指定して実行する場合：

    uv run python -m src \
        --functions_definition data/input/functions_definition.json \
        --input data/input/function_calling_tests.json \
        --output data/output/function_calls.json

出力例：

    [
      {
        "prompt": "What is the sum of 2 and 3?",
        "name": "fn_add_numbers",
        "parameters": {"a": 2.0, "b": 3.0}
      }
    ]

入力ファイルが無い場合や JSON として正しくない場合は、エラーメッセージを標準エラー出力に表示する。
そのあと終了コード 1 で終了し、トレースバックは表示しない。

## アルゴリズムの説明（Algorithm explanation）

### 1. 関数名の判定（`FunctionSelector.select()`）

1. 「設問」から「モデルに渡す文章」を作る（内容は「モデルに渡す文章の作り方」を参照）。
2. 入力②の各「関数名」について、その関数名が「モデルに渡す文章」の続きとして来る確率を LLM で求める。
   - 関数名はいくつかのトークン（単語のかけら）に分かれる。
     各トークンが直前の文章の次に来る確率を logits から softmax で求め、その log（対数確率）を足し合わせて score とする。
   - score は「その関数名が次に来る確率の log」になる。
   - アンダーフローを避けるため、`log_z = max + log(sum(exp(x - max)))`（log-sum-exp）で計算する。
3. score が最も高い関数を、呼び出す関数として選ぶ。
   LLM に自由に書かせず候補の中から選ばせるため、存在しない関数名が出力されることはない。

### 2. 引数の判定（`ConstrainedDecoder.generate_arguments()`）

1. 選んだ関数の引数ごとに「モデルに渡す文章」を作る（内容は「モデルに渡す文章の作り方」を参照）。
2. LLM に引数の値を 1 トークンずつ生成させる。
   1. `get_logits_from_input_ids` で、全トークンの logits を受け取る。
   2. トークン ID を logits の高い順に並べる。
   3. 1 位のトークンが引数の型に合わない場合、値を書き終えたとみなして止める。
   4. それ以外の場合、「今までの値 + トークン」が型の書きかけとして正しいトークンのうち、最も順位の高いものを選ぶ。
      型に合わないトークンを飛ばすことは、そのトークンの logits を負の無限大にすることと同じである。
   5. 型に合うトークンが 1 つも無い場合と、`MAX_NEW_TOKENS`（50）トークンに達した場合にも止める。
3. 生成した値を引数の型に変換し、「引数」としてまとめる。

型ごとに許可する値：

| 型 | 許可する値（書きかけを含む） | 変換後の型 |
| --- | --- | --- |
| `number` | 数字、先頭の `-`、1 個までの `.` | `float` |
| `integer` | 数字、先頭の `-` | `int` |
| `boolean` | `true` または `false` の先頭部分 | `bool` |
| `string` | `"` と改行を含まない文字列 | `str` |

### 3. トークン ID から文字列への変換（`Vocab.to_text()`）

- `get_path_to_vocab_file()` が返す語彙ファイルは、トークンの文字列とトークン ID の対応表である。
  トークンの文字列はバイトレベル BPE の表記で書かれている（`Ġ` はスペース、`Ċ` は改行を表す）。
- `to_text(token_id)` は、トークンの 1 文字ずつを元のバイトに戻し、UTF-8 の文字列に変換する。
  UTF-8 として不完全なバイト列は `�` にする。
- 語彙ファイルに無い ID（特殊トークンや、割り当てのない ID）には空文字列を返す。
  これらの ID は値の一部として選ばれない。

### 4. 出力

出力は `json.dump` で書き込むため、ファイルは常に正しい JSON になる。
各値は関数定義の型に変換するため、出力はスキーマにも合う。

## モデルに渡す文章の作り方（Prompt design）

LLM は「渡された文章の続きとして、次に来やすいトークン」を予測するだけである。
そのため、文章に含めるヒントによって、関数名の判定と引数の判定の正しさが大きく変わる。
このプログラムでは、次の 3 つの方針で文章を作る。

1. **使える関数の一覧を含める**：モデルが設問と関数の説明を結びつけられるようにする。
2. **お手本を 1 つ含める**：答えの形（`Call: <関数名>(<引数名>=<値>, ...)`）を見せる。
3. **関数名の判定と引数の判定で、同じ形の文章を使う**：引数の判定の文章は、関数名の判定の文章の続きを書き進めた形にする。

### 共通の前置き

関数定義ファイルから、使える関数の一覧を作る（`FunctionSelector._make_text_header()`）。
続けて、固定のお手本を 1 つ置く。

```text
Available functions:
- fn_add_numbers(a: number, b: number): Add two numbers together and return their sum.
- fn_greet(name: string): Generate a greeting message for a person by name.
- fn_reverse_string(s: string): Reverse a string and return the reversed result.
- fn_get_square_root(a: number): Calculate the square root of a number.
- fn_substitute_string_with_regex(source_string: string, regex: string, replacement: string): Replace all occurrences matching a regex pattern in a string.

Example:
Question: What is the sum of 10 and 20?
Call: fn_add_numbers(a=10, b=20)
```

- 一覧がないと、モデルは関数名の見た目しか分からない。
  たとえば「Replace all ...」という設問と、`fn_substitute_string_with_regex` を結びつけられない。
- お手本は、答えの形を見せるためのものである。
  引数が 2 つある関数を使い、テストの設問とは違う値（10 と 20）にしている。
  お手本が足し算なので、`fn_add_numbers` が選ばれやすくなるおそれがある。

### 関数名の判定に使う文章（`FunctionSelector.select()`）

共通の前置きの後に、設問を続ける。

```text
（共通の前置き）

Question: What is the sum of 2 and 3?
Call:
```

- この続きに、候補の関数名を 1 つずつ当てはめて score を求める。
- 文章は `Call:` で終わらせ、スペースは関数名の側に付ける（`" fn_add_numbers"`）。
  tokenizer はスペースを次の単語とくっつけて 1 トークンにする（`" fn"` で 1 トークン）ため、
  お手本の `Call: fn_add_numbers` と同じ分かれ方になる。
- 一覧があると、関数名の最初の数トークンが決まれば、残りのトークンはほぼ確実に続く。
  そのため、トークンの多い長い関数名でも score が低くなりにくい。

### 引数の判定に使う文章（`ConstrainedDecoder.generate_arguments()`）

引数 1 つごとに文章を作り、値を書かせたい位置で文章を終わらせる。

```text
Question: What is the sum of 2 and 3?
Call: fn_add_numbers(a=
```

```text
Question: What is the sum of 2 and 3?
Call: fn_add_numbers(a=2, b=
```

```text
Question: Greet shrek
Call: fn_greet(name="
```

- **作り終えた引数を含める**：`b` を作るときは `a=2, ` を含める（`arg_texts`）。
  含めないと、`a` と `b` の文章がほぼ同じになり、モデルが `a` と同じ値を出してしまう。
- **文字列なら `"` まで書く**：値の始まりがはっきりし、モデルは `"` の中に値を書く。
  閉じる `"` は型のチェックで外されるため、そこで生成が止まる。

### 文章の変更による効果

| 変更 | 関数名の判定 | 引数の判定 |
| --- | --- | --- |
| 変更前（設問 + `Function name: `） | 8 / 11 | 2 / 11 |
| 関数名の判定の文章を変更 | 11 / 11 | 2 / 11 |
| 引数の判定の文章も変更 | TODO | TODO |

### 文章では解決できない問題

- 正規表現の `]` が抜ける：モデルが `]"` を 1 トークンで出すため、`"` を含むトークンとして丸ごと外される。
- `\d` が `\\d` になる：`"` の中なので、モデルが `\` を 2 つ重ねて書く。

これらは文章ではなく、トークンの選び方と値の変換で対応する。

## 設計上の判断（Design decisions）

- **関数を自由に生成させず score で選ぶ**：LLM は既存の関数名を比べるだけなので、存在しない関数を作ることはない。
  キーワード判定などのヒューリスティックは使わない。
- **値だけを生成させる**：キーと JSON の構造はプログラムが書き、モデルには引数の値だけを生成させる。
  これにより構造の誤りがなくなり、モデルを呼ぶ回数も減る。
- **`decode` ではなく `vocab.json` を使う**：候補のトークンすべてについて型を判定する。
  自前の対応表を使うことで、任意（optional）の `decode` メソッドに頼らずに済む。
- **pydantic モデル**：入力用のモデル（`FunctionDefinition`・`Prompt`・`ParameterSpec`）は未知のキーを無視し（`extra="ignore"`）、出力用のモデル `FunctionCall` は未知のキーを拒否する（`extra="forbid"`）。
  対応する引数と戻り値の型は `number`・`integer`・`string`・`boolean` で、それ以外の型は `InputFileError` として報告する。
- **エラー処理**：エラーを、`CallMeMaybeError` を基底とする独自の例外（`InputFileError`・`OutputFileError`・`ModelError`・`DecodingError`）に分ける。
  `main()` はこれらと想定外の例外を捕まえて、分かりやすいメッセージを表示し、終了コード 1 を返す。
- **ファイルの読み書き**：`io_utils.py` は、Python 標準の `json` モジュールで JSON を読み書きする。
  ファイルは必ず `with open(...)` で開くため、使い終わったら自動で閉じる。
  `json.load(f)` は JSON ファイルを読み込み、Python のデータ（`dict` / `list`）に変換する（`load_function_definitions()`・`load_prompts()` で使う）。
  `json.dump(data, f)` は Python のデータを JSON に変換し、ファイルに書き込む（`save_function_calls()` で使う）。
  入力ファイルが存在しない場合（`FileNotFoundError`）と、JSON として正しくない場合（`json.JSONDecodeError`）は、どちらも `InputFileError` として扱う。

## 性能の分析（Performance analysis）

> TODO：用意された設問で `make run` を実行したあとに記入する。

| 項目 | 結果 |
| --- | --- |
| 関数選択の正解率 | TODO（正解数 / 全体） |
| 引数の正解率 | TODO |
| 正しい JSON の割合 | TODO |
| 全設問の処理時間 | TODO（目標：5 分以内） |
| 実行環境 | TODO（CPU / GPU、メモリ） |

## 苦労した点（Challenges faced）

- **値の書き終わりの判断**：毎回「型に合う最善のトークン」を選ぶと、モデルは自分では止まらない。
  モデルの 1 位のトークンが型に合わなくなった時点を「値を書き終えたがっている」とみなして止めるようにした。
- **バイトレベル BPE のトークン**：`vocab.json` のトークンの文字列は、そのままの文字列ではない（`Ġis` は `" is"` を表す）。
  バイトの対応表を作り直し、UTF-8 で読み直すようにした。
- **書きかけの数値**：使える文字だけを見る判定では `1.2.3` や `1-2` が通ってしまい、変換で落ちていた。
  `-` は先頭だけ、`.` は 1 個までに制限した。
  さらに、値が書きかけで終わった場合は、変換で `0` / `0.0` を返すようにした。

## テスト方針（Testing strategy）

- `_is_allowed` に、正しい書きかけと正しくない書きかけ（例：`1.2.3`、`1-2`、`--5`、`-1.5`、`-`）を渡して確認した。
- `_convert` に書きかけの値（`-`、`.`、`""`）を渡して、落ちないことを確認した。
- `Vocab.to_text` を、`Ġ`・`Ċ`・複数バイトの文字・途中で切れたバイト列・存在しない ID を含む小さな語彙ファイルで確認した。
- エラー処理を、空の関数定義ファイルと、`Pipeline.run()` の中で想定外の例外を出す場合で確認した。
- `flake8 .` がエラーなしで通ることを確認した。
- TODO：指定のオプション付きの `mypy .` がエラーなしで通ることを確認する。
- TODO：用意された設問の出力を期待する答えと比べる。空文字列・大きな数値・特殊文字・曖昧な設問などの境界のケースも確認する。

## 参考資料（Resources）

- R. Sennrich, B. Haddow, A. Birch, "Neural Machine Translation of Rare Words with Subword Units" (2016)：BPE
- A. Radford et al., "Language Models are Unsupervised Multitask Learners" (2019)：バイトレベル BPE（GPT-2）
- B. Willard, R. Louf, "Efficient Guided Generation for Large Language Models" (2023)：制約付きデコーディング
- Qwen3-0.6B モデルカード：https://huggingface.co/Qwen/Qwen3-0.6B
- Pydantic ドキュメント：https://docs.pydantic.dev/
- uv ドキュメント：https://docs.astral.sh/uv/

### AI の利用

- TODO：AI をどの作業に使い、プロジェクトのどの部分に使ったかを書く。
