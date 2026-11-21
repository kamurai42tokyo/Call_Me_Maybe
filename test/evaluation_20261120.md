# テスト結果の評価（2026-11-20）

## 実行条件

- 入力：`data/input/functions_definition.json`、`data/input/function_calling_tests.json`（11 問）
- 出力：`data/output/function_calling_results.json`（2026-11-20 06:27 に生成）
- モデル：Qwen/Qwen3-0.6B
- 実行時間：TODO（`time make run` で計測する）
- モデルに渡す文章（共通の前置き = 関数の一覧 + お手本）
  - 関数名の判定：共通の前置き + `Question: <設問>\nCall:`
  - 引数の判定：共通の前置き + `Question: <設問>\nCall: <関数名>(<作り終えた引数><引数名>=`（文字列の場合は最後に `"`）
- 値の後処理
  - 閉じる `"` を含むトークン（例：`)"`）が出た場合、`"` より前の部分は値に含めてから終える
  - 文字列の値の `\\` を `\` に戻す

## 判定方法

- 正解ファイルは無いため、設問の意味から正しい答えを考えて判定した。
- `fn_substitute_string_with_regex` の 3 問は、出力された引数で Python の `re.sub(regex, replacement, source_string)` を実行して確かめた。

## まとめ

| 項目 | 結果 |
| --- | --- |
| 正しい JSON | 11 / 11 |
| 引数の型が関数定義どおり | 11 / 11 |
| 関数の選択 | 11 / 11 |
| 引数まで完全に正解 | 11 / 11 |

## 各設問の判定

| # | 設問 | 選ばれた関数 | 生成された引数 | 判定 |
| --- | --- | --- | --- | --- |
| 1 | What is the sum of 2 and 3? | `fn_add_numbers` ✅ | `a=2.0, b=3.0` | ✅ |
| 2 | What is the sum of 265 and 345? | `fn_add_numbers` ✅ | `a=265.0, b=345.0` | ✅ |
| 3 | Greet shrek | `fn_greet` ✅ | `name="shrek"` | ✅ |
| 4 | Greet john | `fn_greet` ✅ | `name="john"` | ✅ |
| 5 | Reverse the string 'hello' | `fn_reverse_string` ✅ | `s="hello"` | ✅ |
| 6 | Reverse the string 'world' | `fn_reverse_string` ✅ | `s="world"` | ✅ |
| 7 | What is the square root of 16? | `fn_get_square_root` ✅ | `a=16.0` | ✅ |
| 8 | Calculate the square root of 144 | `fn_get_square_root` ✅ | `a=144.0` | ✅ |
| 9 | Replace all numbers in "Hello 34 I'm 233 years old" with NUMBERS | `fn_substitute_string_with_regex` ✅ | `source_string="Hello 34 I'm 233 years old"`, `regex="\d+"`, `replacement="NUMBERS"` | ✅ 実行結果は `"Hello NUMBERS I'm NUMBERS years old"` |
| 10 | Replace all vowels in 'Programming is fun' with asterisks | `fn_substitute_string_with_regex` ✅ | `source_string="Programming is fun"`, `regex="[aeiou]"`, `replacement="*"` | ✅ 実行結果は `"Pr*gr*mm*ng *s f*n"` |
| 11 | Substitute the word 'cat' with 'dog' in 'The cat sat on the mat with another cat' | `fn_substitute_string_with_regex` ✅ | `source_string="The cat sat on the mat with another cat"`, `regex="cat"`, `replacement="dog"` | ✅ 実行結果は `"The dog sat on the mat with another dog"` |

※ 9 番の `regex` は、中身が `\d+`（`\` が 1 つ）である。出力ファイル（JSON）の中では、`\` が `\\` と書かれるため `"\\d+"` と見える。

## 前回からの変化

| # | 前回の結果 | 今回の結果 | 直った理由 |
| --- | --- | --- | --- |
| 3 | `name="Shrek"`（先頭が大文字） | `name="shrek"` | 引数の判定の文章にも、共通の前置きを含めた |
| 9 | `regex="([0-9]+"`（`)` が抜けて `re.sub` がエラー） | `regex="\d+"` | `"` より前の部分を値に残すようにした。また、`\\` を `\` に戻すようにした |
| 10 | `regex=".*[aeiouAEIOU].*"`, `replacement="**"`（文全体が置き換わる） | `regex="[aeiou]"`, `replacement="*"` | 引数の判定の文章にも、共通の前置きを含めた |

## これまでの推移

| 変更 | 関数の選択 | 引数 |
| --- | --- | --- |
| 変更前（設問 + `Function name: `） | 8 / 11 | 2 / 11 |
| 関数名の判定の文章を変更 | 11 / 11 | 2 / 11 |
| 引数の判定の文章を変更（作り終えた引数と `"` を含める） | 11 / 11 | 8 / 11 |
| `"` を含むトークンの前の部分を値に残す | 11 / 11 | 9 / 11 |
| 引数の判定の文章に共通の前置きを含める + `\\` を `\` に戻す（今回） | 11 / 11 | 11 / 11 |
