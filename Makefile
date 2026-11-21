# ============================== 変数の定義 ==============================
#
# UV                     		: パッケージ管理ツール uv のコマンド名
# RUN                    		: 仮想環境の中でコマンドを実行する (uv run)
# UV_PROJECT_ENVIRONMENT 		: 仮想環境 (.venv) の作成先。ホームの容量節約のため goinfre に置く
# UV_CACHE_DIR           		: uv のダウンロードキャッシュの保存先。同じく goinfre に置く
# MYPY_FLAG              		: make lint で mypy に渡す型チェックのオプション
#   --warn-return-any          	: Any 型を返す関数を警告する
#   --warn-unused-ignores      	: 不要な "# type: ignore" を警告する
#   --ignore-missing-imports   	: 型情報のないライブラリの import エラーを無視する
#   --disallow-untyped-defs    	: 型ヒントのない関数定義をエラーにする
#   --check-untyped-defs       	: 型ヒントのない関数の中身もチェックする
#

UV								:= uv
RUN								:= $(UV) run
export UV_PROJECT_ENVIRONMENT	:= /goinfre/$(USER)/cmm_venv
export UV_CACHE_DIR				:= /goinfre/$(USER)/uv_cache


MYPY_FLAG						:= 	--warn-return-any \
									--warn-unused-ignores \
									--ignore-missing-imports \
									--disallow-untyped-defs \
									--check-untyped-defs


# ============================= ルールの定義 =============================

usage:
	@echo "Usage: make [target]"
	@echo ""
	@echo " install		　依存パッケージをインストール"
	@echo " run			　プログラムを実行"
	@echo " debug		　pdbでデバッグ実行"
	@echo " clean		　キャッシュを削除"
	@echo " lint		　flake8 + mypy でチェック"
	@echo " lint-strict	　mypy --strict でチェック"

install:
	$(UV) sync

run:
	$(RUN) python -m src $(ARGS)

debug:
	$(RUN) python -m pdb -m src

clean:
	rm -rf src/__pycache__ .mypy_cache .pytest_cache

lint:
	$(RUN) flake8
	$(RUN) mypy . $(MYPY_FLAG)

lint-strict:
	$(RUN) flake8
	$(RUN) mypy . --strict

.PHONY: usage install run debug clean lint lint-strict
