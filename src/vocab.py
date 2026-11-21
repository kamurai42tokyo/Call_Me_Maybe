#!/usr/bin/env python3

"""トークン ID（モデルが扱う番号）と文字列の対応表を扱う。

Vocab: llm_sdk が返す語彙ファイル（vocab.json）を読み込み、
    「ID → 文字列」の辞書として保持する。
"""

import json


class Vocab:
    """トークン ID と文字列の対応表を扱う。"""

    def __init__(self, vocab_path: str) -> None:
        """語彙ファイルを読み込み、「ID → 文字列」の辞書を作って保持する。

        Args:
            vocab_path: llm_sdk が返す語彙ファイル（vocab.json）のパス。
        """
        # 語彙ファイルのパスから、「文字列→ID」の辞書を作成する
        with open(vocab_path, "r", encoding="utf-8") as f:
            self._text_to_id: dict[str, int] = json.load(f)

        # 「文字列→ID」の辞書から「ID→文字列」の辞書を作成する
        self._id_to_text: dict[int, str] = {
            id: text for text, id in self._text_to_id.items()
        }

        # byte-level BPE の１文字は、正しい１文字ではない。
        # 「Ġ みたいな文字 → 元のバイト」への変換が必要。
        # まずはその「対応表」を作る。
        #
        # printable     : 見える文字そのままのバイト値のリスト
        # byte_decoder : １文字 → バイト値の対応表（辞書）
        #
        self._printable: list[int] = (
            list(range(ord("!"), ord("~") + 1))
            + list(range(ord("¡"), ord("¬") + 1))
            + list(range(ord("®"), ord("ÿ") + 1))
        )
        self._byte_decoder: dict[str, int] = \
            {chr(byte): byte for byte in self._printable}

        # バイト値 0〜255 を順番に見て、その内 printable に存在しない文字を
        # 見えない文字（改行やスペース）として、byte_decoder の 257 以降の
        # バイト値へ順に割り当てる。
        n: int = 0
        for byte in range(256):
            if byte not in self._printable:
                self._byte_decoder[chr(256 + n)] = byte
                n += 1

    def to_text(self, token_id: int) -> str:
        """トークン ID を、対応する文字列に変換する。

        Small_LLM_Model.decode([token_id]) と同じ文字列を返す。
        （例: "Ġis" に対応する ID なら " is"）

        Args:
            token_id: 変換するトークン ID。

        Returns:
            トークン ID に対応する文字列。語彙ファイルに無い ID
            （特殊トークンなど）の場合は空文字列を返す。
        """
        # ID に対応する文字列を取り出す（無い ID なら "" を返す）
        vocab_token: str | None = self._id_to_text.get(token_id)
        if not vocab_token:
            return ""

        # vocab.json の１文字ずつを、byte_decoder（対応表）に従って
        # 生のバイト値へ順に変換していき、まとめて返す。
        raw_bytes: list[int] = []
        for c in vocab_token:
            raw_byte: int = self._byte_decoder[c]
            raw_bytes.append(raw_byte)
        return bytes(raw_bytes).decode("utf-8", errors="replace")
