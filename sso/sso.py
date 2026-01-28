import sys
import cmd
import readline  # 矢印キー・履歴が有効
from lark import Lark, Token
from interpreter import SSOInterpreter
from classes import SSOSystemConfig

import logging # ログの設定
logging.basicConfig(
level=logging.DEBUG, # 出力レベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger =  logging.getLogger(__name__)

class SSOShell(cmd.Cmd):
    intro = "Solar System Observer (SSO) DSL - Interpreter Mode\n(Type 'exit' to quit)"
    prompt = "sso> "

    def __init__(self):
        super().__init__()
        # 文法ファイルの読み込み
        try:
            with open("sso.lark", "r", encoding="utf-8") as f:
                grammar = f.read()
            self.parser = Lark(grammar, parser='lalr')
            self.interp = SSOInterpreter()
        except FileNotFoundError:
            print("Error: 'sso.lark' file not found.")
            sys.exit(1)

    def default(self, line):
        if not line.strip():
            return
        try:
            # 1. パースを実行（末尾に改行を付けて文末を認識させる）
            tree = self.parser.parse(line + "\n")

            # 慣れるまで、解析木を表示する
            logger.debug(tree.pretty())

            # e. visit(tree) を実行。結果は通常 [結果1, Token, 結果2...] のリストで返る
            results = self.interp.visit(tree)
            logger.info(results)

            # 3. 表示処理。結果が単一でもリストでも対応できるようにする
            if not isinstance(results, list):
                results = [results] # 単一の結果をリストに包んで共通処理へ
                #「リストの強要」というテクニックらしい

            for res in results:
                # Token(改行等)は無視
                if isinstance(res, Token):
                    continue

                # リストが入れ子（ネスト）になっている場合を想定して再帰的に処理
                if isinstance(res, list):
                    for sub_res in res:
                        if not isinstance(sub_res, Token) and sub_res is not None:
                            if self.interp.config.env["Echo"]:
                                print(sub_res)
                else:
                    # 通常の出力
                    if res is not None and self.interp.config.env["Echo"]:
                        logger.debug(f"return type: {type(res)}")
                        # type() が <class 'ephem.Date'> なら Tz を加算する
                        if f"{type(res)}" == "<class 'ephem.Date'>":
                            logger.debug(f"Date change: UTC -> UTC+Tz")
                            print(f"UTC: {res}")
                            print(f"UTC+Tz: {self.interp.config.fromUTC(res)}")
                        print(res)

        except Exception as e:
            print(f"Error: {e}")

    # --- シェル制御コマンド ---
    def do_exit(self, arg):
        """終了コマンド"""
        return True # Trueを返すとループが終了する

    def do_quit(self, arg):
        """終了コマンド"""
        return True

    # EOF (Ctrl+D) での終了対応
    def do_EOF(self, arg):
        print()
        return True

if __name__ == "__main__":
    try:
        SSOShell().cmdloop()
    except KeyboardInterrupt:
        # Ctrl+C での強制終了をきれいに処理
        print("\nGoodbye.")
