import sys
import cmd
import ephem
import readline  # 矢印キー・履歴が有効
from lark import Lark, Token
from interpreter import SSOInterpreter
from classes import SSOSystemConfig

import logging # ログの設定
logging.basicConfig(
level=logging.WARNING, # 出力レベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
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

    def emptyline(self):
        # 何もしないように上書き（これがないと直前のコマンドが走る）
        pass

    def reset_observation_environment(self):
        self.interp.config.env['Time'] = self.interp.config.SSOEphem("now")
        self.interp.var_mgr.observer = {}

    def default(self, line):
        if not line.strip():
            return
        try:
            log_mode = self.interp.config.env["Log"].strip('"')

            if log_mode == "Yes":
                logging.disable(logging.NOTSET)
            elif log_mode == "No":
                logging.disable(logging.CRITICAL)
            else:
                level = getattr(logging, log_mode, logging.CRITICAL)
                logging.disable(level)

            # 観測環境をリセット（観測日時、Bodyの観測日指定）
            self.reset_observation_environment()

            # パースを実行（末尾に改行を付けて文末を認識させる）
            tree = self.parser.parse(line + "\n")

            # 慣れるまで、解析木を表示する
            logger.debug(tree.pretty())

            # visit(tree) を実行。結果は通常 [結果1, Token, 結果2...] のリストで返る
            results = self.interp.visit(tree)
            logger.info(results)

            # 表示処理。結果が単一でもリストでも対応できるようにする
            if not isinstance(results, list):
                results = [results] # 単一の結果をリストに包んで共通処理へ
                # 「リストの強要」というテクニックらしい

            for res in results:
                # Token(改行等)は無視
                if isinstance(res, Token):
                    continue

                # リストが入れ子（ネスト）になっている場合を想定して再帰的に処理
                if isinstance(res, list):
                    for sub_res in res:
                        if not isinstance(sub_res, Token) and sub_res is not None:
                            if self.interp.config.env["Echo"] == "Yes":
                                print(sub_res)
                else:
                    # 通常の出力
                    if res is not None and (self.interp.config.env["Echo"] == "Yes"):
                        logger.debug(f"return type: {type(res)}")
                        match res:
                            case ephem.Date():
                                # <class 'ephem.Date'> なら Tz を加算する
                                print(f"{self.interp.config.fromUTC(res)}")
                            case float() | str() | int():
                                print(res)
                            case _:
                                pass

        except Exception as e:
            print(f"Error: {e}")

    # --- シェル制御コマンド ---
    def do_hello(self, arg):
        print(f"Hello {arg}!")

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
