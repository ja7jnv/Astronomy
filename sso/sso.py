# TODO - 入力補完 (Autocompletion): Earth や Moon などのキーワードを途中まで打ったら補完候補を出す。

import logging # ログの設定
logging.basicConfig(
level=logging.WARNING, # 出力レベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger =  logging.getLogger(__name__)

import sys
import cmd
import ephem
import readline  # 矢印キー・履歴が有効
from lark import Lark, Token
from interpreter import SSOInterpreter
from classes import SSOSystemConfig, SSOLexer
from classes import console

# 入力中のコマンドにシンタックスハイライト
from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.formatted_text import HTML
from pygments import highlight
from pygments.formatters import TerminalFormatter

from prompt_toolkit.styles.pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name

# 黒背景に映える鮮やかな配色を適用
#selected_style = style_from_pygments_cls(get_style_by_name('monokai'))
#selected_style = style_from_pygments_cls(get_style_by_name('fruity'))
#selected_style = style_from_pygments_cls(get_style_by_name('native'))
selected_style = style_from_pygments_cls(get_style_by_name('paraiso-dark'))

#from prompt_toolkit.styles import Style
# ハイライト用スタイルの定義
"""
style = Style.from_dict({
    'command': '#4af626 bold',  # コマンドを緑色に
    'argument': '#aaaaaa',      # 引数をグレーに
})
"""
from rich.console import Console
from rich.panel import Panel

class SSOShell(cmd.Cmd):
    # prompt_toolkitで使うためのHTMLタグ付きプロンプト
    # <style名>テキスト</style名> の形式で記述
    colored_prompt = HTML('<ansicyan>sso</ansicyan><ansigray>></ansigray> ')

    intro = "Solar System Observer (SSO) DSL - Interpreter Mode\n(Type 'exit' to quit)"
    intro_text = """
[bold magenta]SSO Celestial Navigation System[/bold magenta] [dim]v1.0[/dim]
[cyan]Type 'help' for commands, 'exit' to quit.[/cyan]
    """
    prompt = "sso> "

    def __init__(self):
        super().__init__()
        
        # 入力ハイライト用のセッション
        self.session = PromptSession(
                lexer=PygmentsLexer(SSOLexer),
                style=selected_style
        )

        # 文法ファイルの読み込み
        try:
            with open("sso.lark", "r", encoding="utf-8") as f:
                grammar = f.read()
            self.parser = Lark(grammar, parser='lalr')
            self.interp = SSOInterpreter()

        except FileNotFoundError:
            print("Error: 'sso.lark' file not found.")
            sys.exit(1)


    def cmdloop(self, intro=None):
        #print(intro or "DSL Shell Started. (Ctrl+D to exit)")
        # 標準のイントロ表示をスキップし、Richで表示
        console.print(Panel(self.intro_text, border_style="blue"))
        while True:
            try:
                # 入力中のハイライト適用
                #text = self.session.prompt(self.prompt)
                text = self.session.prompt(self.colored_prompt)
                if text.strip():
                    self.onecmd(text)
            except EOFError: break
            except KeyboardInterrupt: continue

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
