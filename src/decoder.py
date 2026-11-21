#!/usr/bin/env python3

"""選ばれた関数の引数の値を、型に合う形で LLM に生成させる。

ConstrainedDecoder: 型に合わないトークンを候補から外しながら、
    引数の値をトークン 1 つずつ生成し、引数の型の値に変換する。
"""

from .models import FunctionDefinition, Prompt
from .vocab import Vocab
from llm_sdk import Small_LLM_Model

# 1つの引数の値を作るときに生成するトークン数の上限（モデルが止まらない場合の安全装置）
# 単位は文字数ではなくトークン数。英文ならおよそ 150〜200 文字分に相当する
MAX_NEW_TOKENS = 50


class ConstrainedDecoder:
    """選ばれた関数の引数の値を、型に合う形で LLM に生成させる。

    モデルが返す点数（logits）の高い順に候補を見て、引数の型に合う
    トークンだけを 1 つずつ選んで値を作る（制約付きデコーディング）。
    """

    def __init__(
            self,
            model: Small_LLM_Model,
            vocab: Vocab,
            text_header: str
            ) -> None:
        """デコーダを初期化する。

        Args:
            model: トークンの予測に使う LLM モデル。
            vocab: トークン ID と文字列の対応を扱う語彙。
        """
        self._model: Small_LLM_Model = model
        self._vocab: Vocab = vocab
        self._text_header: str = text_header

    def generate_arguments(
            self, prompt: Prompt, selected_function: FunctionDefinition
            ) -> dict[str, float | int | str | bool]:
        """選ばれた関数の引数の値を、型に合う形で LLM に生成させる。

        引数ごとに「モデルに渡す文章」（設問文 + 関数名 + "引数名 = "）を作り、
        その続きとして、引数の型に合うトークンの中で logits が最も高いものを
        1 つずつ選んで値を作る。モデルが最も推すトークンが型に合わなくなったら、
        値を書き終えたとみなして止め、作った文字列を引数の型に変換する。

        Args:
            prompt: ユーザーからの入力プロンプト。
            selected_function: 呼び出す関数として選ばれた関数定義。

        Returns:
            引数名をキー、生成した値を値とする辞書。
            値の型は関数定義で指定された型（float / int / str / bool）になる。
        """
        # 選ばれた関数における各引数名をkeyとし、その値をvalueとする辞書
        arguments: dict[str, float | int | str | bool] = {}

        # 作り終えた引数を "引数名=値" の形でためておくリスト（例: ["a=2"]）
        arg_texts: list[str] = []

        # selected_function.parameters から、引数名と型を1個ずつ取り出す。
        for name, spec in selected_function.parameters.items():

            # 文字列の引数ならspec、値の始まりを示す " を付ける
            quote: str = '"' if spec.type == "string" else ""

            # 作り終えた引数を "a=2" の形でつなげる
            prefix: str = "".join(f"{d}, " for d in arg_texts)

            # 「モデルに渡す文章」を作成
            # 例）Call: fn_add_numbers(a=2, b=
            text: str = (
                f"{self._text_header}"
                f"Question: {prompt.prompt}\n"
                f"Call: {selected_function.name}({prefix}{name}={quote}"
            )

            # 「モデルに渡す文章」を、トークンID（単語のかけらに付けた番号）のリストに変換する
            ids: list[int] = self._model.encode(text)[0].tolist()

            # LLMが作った引数の値を、トークン１個ずつ継ぎ足して貯めていく文字列の入れ物
            # 例: 質問「40 と 2 を足すと？」で、引数 a の型が int の場合
            #   1回目: "a = "   の続きで 1位が "4"  → int に合う → value_text = "4"
            #   2回目: "a = 4"  の続きで 1位が "0"  → int に合う → value_text = "40"
            #   3回目: "a = 40" の続きで 1位が "\n" → int に合わない → ここで止める
            #   付け足したトークンは ids にも追加し、次の回はそれ込みでモデルに見せる
            value_text: str = ""

            # トークンを１個ずつ作る処理を、最大 MAX_NEW_TOKENS 回を上限として繰り返す
            for _ in range(MAX_NEW_TOKENS):

                # 「モデルに渡す文章」を実際にモデルに読ませ、「次に来るトークン」の
                # 候補全部についての出やすさの“点数”を取得する。
                logits: list[float] = \
                    self._model.get_logits_from_input_ids(ids)

                # トークンIDを点数の高い順に並べる
                order: list[int] = sorted(
                    range(len(logits)), key=lambda i: logits[i], reverse=True)

                # 1位のトークンが型に合わない場合、モデルが値を書き終えたと判断して
                # 値の生成を終える
                top_text: str = self._vocab.to_text(order[0])
                if value_text and not self._is_allowed(
                        value_text + top_text, spec.type):
                    # 【困ること】
                    # モデルは文字を 1 文字ずつではなく、トークン（文字のかたまり）で出す。
                    # 値の最後で、")" と閉じる '"' がくっついた ')"' というトークンが出ることがある。
                    # '"' を含むトークンは型のチェックで捨てられるため、
                    # このままだと、値に必要な ")" まで一緒に捨てられてしまう。
                    #   例: "([0-9]+" の次に ')"' が出る → ")" が消えて "([0-9]+" のまま終わる
                    #
                    # 【対策】
                    # トークンを '"' のところで切り、左側（'"' より前の部分）だけを値に足してから終える。
                    #   例: ')"' → ')' だけ足す → "([0-9]+)" になる
                    if spec.type == "string" and '"' in top_text:
                        # トークンを '"' で切った左側（例: ')"' → ')'）
                        before_quote: str = top_text.split('"')[0]
                        # 左側に改行などの使えない文字が無いことを確かめてから足す
                        if self._is_allowed(
                                value_text + before_quote, spec.type):
                            value_text += before_quote
                    break

                # 点数の高い順に見て、型に合う最初のトークンを選ぶ
                found_token: bool = False
                for token_id in order:
                    # トークンIDを、元の文字列に戻す
                    token_text: str = self._vocab.to_text(token_id)

                    # 空でないトークンで、今までの値に足しても型の書きかけとして正しければ、
                    # 「見つかった」として候補探しを終える
                    if token_text and self._is_allowed(
                            value_text + token_text, spec.type):
                        found_token = True
                        value_text += token_text
                        ids.append(token_id)
                        break

                # 型に合うトークンが 1 つも見つからなければ、これ以上値を伸ばせないので
                # 値づくりを終える（外側のループを抜ける）
                if not found_token:
                    break

            # 生成した文字列を、引数の型の値に変換する
            arguments[name] = self._convert(value_text, spec.type)

            # 作り終えた引数を "引数名=値" の形で記録する（例: "a=2"）
            # 次の引数の文章に「この値はもう決まった」と含めることで、
            # モデルが前の引数と同じ値を出してしまうのを防ぐ
            arg_texts.append(f"{name}={quote}{value_text}{quote}")

        # 選ばれた関数の各引数における値を返す
        return arguments

    @staticmethod
    def _is_allowed(text: str, type_name: str) -> bool:
        """text が、引数の型の値の書きかけとして正しいかを判定する。

        値はトークンを 1 つずつ足して作るため、完成した値でなくても、
        このあと正しい値になり得る途中の文字列であれば True とする。

        Args:
            text:
                判定する文字列。今まで作った値に、次の候補トークンを
                足したもの（value_text + token_text）が渡される。
            type_name:
                引数の型の名前。
                "number" / "integer" / "string" / "boolean" のいずれか。

        Returns:
            型に合う書きかけなら True、合わなければ False。
        """
        if type_name == "number":
            text = text.lstrip(" ")
            return (
                all(c in "0123456789.-" for c in text)
                and "-" not in text[1:]
                and text.count(".") <= 1
            )
        elif type_name == "integer":
            text = text.lstrip(" ")
            return (
                all(c in "0123456789-" for c in text)
                and "-" not in text[1:]
            )
        elif type_name == "boolean":
            return "true".startswith(text) or "false".startswith(text)
        else:
            return '"' not in text and "\n" not in text

    @staticmethod
    def _convert(text: str, type_name: str) -> float | int | str | bool:
        """生成した文字列を、引数の型に合う Python の値に変換する。

        モデルが作った値は文字列（例: "40"）のままなので、関数定義の型に
        合わせて変換する（例: 型が "number" なら "40" → 40.0）。

        Args:
            text:
                変換する文字列。トークンを継ぎ足して作った value_text が渡される。
            type_name:
                引数の型の名前。
                "number" / "integer" / "string" / "boolean" のいずれか。

        Returns:
            変換後の値。"number" なら float、"integer" なら int、
            "boolean" なら bool、"string" なら str をそのまま返す。
        """
        if type_name == "number":
            try:
                return float(text)
            except ValueError:
                return 0.0
        elif type_name == "integer":
            try:
                return int(text)
            except ValueError:
                return 0
        elif type_name == "boolean":
            return text == "true"
        else:
            # モデルは "..." の中で \ を \\ と重ねて書くため、元の 1 つに戻す
            #   例: "\\d+" → "\d+"
            return text.replace("\\\\", "\\")
