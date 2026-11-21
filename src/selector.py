#!/usr/bin/env python3

"""設問 1 件に対して、呼び出す関数を LLM で 1 つ選ぶ。

FunctionSelector: 各関数名が設問の続きとして来る確率（log）をモデルで求め、
    最も確率が高い関数を選ぶ。
"""

from .models import FunctionDefinition, Prompt
from llm_sdk import Small_LLM_Model
import math


class FunctionSelector:
    """設問に対して、関数定義の中から呼び出す関数を 1 つ選ぶ。

    候補の関数名ごとに、「モデルに渡す文章」の続きとしてその関数名が来る
    確率の log（score）をモデルで求め、score が最も高い関数を選ぶ。
    """

    def __init__(
            self,
            model: Small_LLM_Model,
            function_definitions: list[FunctionDefinition]
            ) -> None:
        """選択に使うモデルと、候補となる関数定義を受け取って保持する。

        Args:
            model: 次に来るトークンの点数（logits）を求めるための言語モデル。
            vocab: トークンIDと文字列の対応表。
            function_definitions: 関数定義ファイルから読み込んだ、候補の関数定義のリスト。
        """
        self._model: Small_LLM_Model = model
        self._function_definitions: list[FunctionDefinition] = \
            function_definitions
        self._result_example: str = (
            "Example:\n"
            "Question: What is the sum of 10 and 20?\n"
            "Call: fn_add_numbers(a=10, b=20)"
        )

        self.text_header: str = (
            f"{self._make_text_header()}\n\n"
            f"{self._result_example}\n\n"
        )

    def _make_text_header(self) -> str:
        """_summary_

        ex) Available functions:
        - fn_add_numbers(a: number, b: number): Add two numbers ...
        - fn_greet(name: string): Generate a greeting message fo...
        - fn_reverse_string(s: string): Reverse a string and ret...
        ...

        Returns:
            str: _description_
        """
        header_text: list[str] = ["Available functions:"]
        for fd in self._function_definitions:
            a_line: str = f"- {fd.name}("
            for i, (key, value) in enumerate(fd.parameters.items()):
                if i:
                    a_line += ", "
                a_line += f"{key}: {value.type}"
            a_line += f"): {fd.description}"
            header_text.append(a_line)
        return "\n".join(header_text)

    def select(self, prompt: Prompt) -> FunctionDefinition:
        """設問 1 件に対して、最もふさわしい関数定義を 1 つ選んで返す。

        「モデルに渡す文章」（設問文 + "Function name: "）の続きとして、
        各候補の関数名が来る確率の log（score）を求め、score が最も高い
        関数定義を返す。

        Args:
            prompt: 設問ファイルから読み込んだ設問 1 件。

        Returns:
            候補の中で score が最も高い関数定義。
        """

        # 「モデルに渡す文章」を作成
        text: str = (
            f"{self.text_header}"
            f"Question: {prompt.prompt}\n"
            "Call:"
            )

        # 「モデルに渡す文章」を、トークンID（単語のかけらに付けた番号）のリストに変換する
        #
        # Small_LLM_Model.encode(text):
        # - Small_LLM_Model クラスに定義されているメソッド
        # - 文字列を、モデルが読めるトークンIDの並びに変換する
        # - [[ID1, ID2, ...]] のように、トークンIDの入れ物を２次元のリストで返す。
        #
        # Small_LLM_Model.encode(text)[0]:
        # - Small_LLM_Model.encode(text) の返り値は２次元配列のため、
        # 　[0]で中身の要素を取り出している。
        #
        # Small_LLM_Model.encode(text)[0].tolist():
        # - Small_LLM_Model.encode(text)[0] は Tensor 型なので、
        #   .tolist() を付けることで、int 型に直す。
        #
        base_ids: list[int] = self._model.encode(text)[0].tolist()

        # 関数定義ファイル内の１つ目の関数を暫定の１位（best）とし、
        # 評価点数を -inf にする。
        best: FunctionDefinition = self._function_definitions[0]
        best_score: float = float("-inf")

        # 関数定義ファイル内の関数を１つずつ取り出す。
        for function_definition in self._function_definitions:

            # 「モデルに渡す文章」をコピーして保持する。
            ids: list[int] = list(base_ids)
            score: float = 0.0

            # 関数名を構成するトークンIDを１つずつ取り出す。
            name_ids: list[int] = \
                self._model.encode(" " + function_definition.name)[0].tolist()
            for token_id in name_ids:

                # 「モデルに渡す文章」を実際にモデルに読ませ、「次に来るトークン」の
                # 候補全部についての出やすさの“点数”を取得する。
                logits: list[float] = \
                    self._model.get_logits_from_input_ids(ids)

                # 「次に来るトークン」の候補全部についての出やすさの“点数”の中で、
                # 最も高い点数を取得する。
                max_logit = max(logits)

                # 【目的】
                # 候補の関数名が、「モデルに渡す文章」の続きとして来る確率を求める。
                #
                # 関数名はいくつかのトークンで構成されているため、その関数名が次に来る確率は、
                # 各トークンが直前の文章の次に来る確率の積になる。
                #   例: 次に「fn_add」が来る確率
                #       ＝「fn」が次に来る確率 × 「fn」の後に「_add」が次に来る確率
                #
                # そこで、候補の関数名の各トークンについて、そのトークンが次に来る確率を求め、
                # その確率の log（対数確率）を、確率の積（score）に足し合わせる。
                # ※log をとる理由は後述。
                #
                # 関数名の全トークン分を足し終えた確率の積（score）が、「その関数名が次に来る
                # 確率として比較できる値」になり、その値を用いて、関数名同士で比較が可能になる。
                #
                # 【手段】
                # モデルが返す logits は確率ではなく、語彙の全トークンに付いた生の点数なので、
                # softmax という計算方法で、「語彙の各トークンが、直前の文章の次に来る確率」に直す。
                #
                # softmax:
                #   確率 = exp(そのトークンの点数) ÷ 全トークンの exp(点数) の合計
                #
                # 両辺の log をとると:
                #   log(確率) = そのトークンの点数 − log(全トークンの exp(点数) の合計)
                #             = logits[token_id] − log_z
                #
                # 【log をとる理由】
                # 1. 1トークンの確率は小さい（例: 0.001）ことが多く、確率のまま掛け続けると
                #    0 に近づきすぎて float で表せなくなる（アンダーフロー）。
                #    log なら「-6.9 + -6.9 + …」のように通常の大きさの数で計算できる。
                # 2. log(a × b) = log(a) + log(b) なので、確率の積を足し算で求められる。
                # 3. 確率が大きいほど log も大きいため、log のまま比較しても
                #    選ばれる関数名は変わらない。
                # 4. softmax を log の形にすると logits[token_id] − log_z の引き算で済み、
                #    確率を求めてから log をとる手間が省ける。
                #
                log_z = max_logit + math.log(
                    sum(math.exp(x - max_logit) for x in logits))
                score += logits[token_id] - log_z

                # 今計算していたトークンIDについて、次のループでその続きを予測するために
                # 「モデルに渡す文章」（ids）の末尾にくっつける。
                ids.append(token_id)

            # 「モデルに渡す文章」の続きとして来る確率が最も高い関数を採用する。
            if score > best_score:
                best, best_score = function_definition, score

        # 「モデルに渡す文章」の続きとして来る確率が最も高いもの関数を返す。
        return best
