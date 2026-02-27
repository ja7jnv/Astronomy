import logging # ログの設定
logging.basicConfig(
level=logging.WARNING, # 出力レベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger =  logging.getLogger(__name__)

# 基幹部分の外部システムをインポート
import sys
import cmd
import unicodedata
import os
import ephem
from datetime import datetime

import readline  # 矢印キー・履歴が有効
from lark import Lark, Token
from lark.exceptions import UnexpectedToken, UnexpectedEOF

# プロジェクト内のクラスのインポート
from interpreter import SSOInterpreter
from classes import SSOSystemConfig, SSOLexer
from classes import console
from classes import Constants
from ssohelp import Body_help

# 以下、見栄えを改善するための外部システムのインポート

# 入力中のコマンドにシンタックスハイライト
from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.formatted_text import HTML
from pygments import highlight
from pygments.formatters import TerminalFormatter

from prompt_toolkit.styles.pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name

from completer import sso_completer

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
    ## ここでHelpの見出しをカスタマイズ
    misc_header = "その他のガイド・解説:"
    doc_header = "実行可能なコマンド一覧:"
    undoc_header = "ヘルプ未作成のコマンド:"
    #ruler = "-"  # 見出しの下の線を「-」に変更（デフォルトは「=」）

    # prompt_toolkitで使うためのHTMLタグ付きプロンプト
    # <style名>テキスト</style名> の形式で記述
    colored_prompt = HTML('<ansicyan>sso</ansicyan><ansigray>></ansigray> ')

    intro = "Solar System Observer (SSO) DSL - Interpreter Mode\n(Type 'exit' to quit)"
    intro_text = """
[bold magenta]SSO 太陽系観測シミュレータ[/bold magenta] [dim]機能確認版 V0.1[/dim]

    [cyan]Type 'help' for commands, 'exit' to quit.[/cyan]

    Copyright (C) 2026 Shigeaki Tendo
    """
    continue_prompt = "... "

    def __init__(self):
        super().__init__()
        self.code_buffer = ""
        
        # 入力ハイライト用のセッション
        self.session = PromptSession(
                lexer=PygmentsLexer(SSOLexer),  # シンタックスハイライト
                completer=sso_completer,        # 補完機能
                style=selected_style            # 出力のハイライト
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
        self.code_buffer = ""
        stop = None
        while not stop:
            logger.debug(f"start parser code_buffer:{self.code_buffer}")
            if self.code_buffer == "\n": self.code_buffer = ""
            try:
                if self.code_buffer:
                    prompt = self.continue_prompt
                else:
                    prompt = self.colored_prompt
                text = self.session.prompt(prompt, reserve_space_for_menu=0)
            except EOFError:
                logger.debug(f"text: {text}")
                break
            except KeyboardInterrupt: continue

            self.code_buffer += text + "\n"
            logger.debug(f"code_buffer:\n*start_sentence*\n{self.code_buffer}*end_sentence*")
            if self.code_buffer.strip():
                logger.debug(f"Evaluate code_buffer:\n**BEGIN**\n{self.code_buffer}**END**")
                #self.onecmd(self.code_buffer)

                stop = self.onecmd(text)
                #self.postcmd(stop, text)

    # 実行直後に呼ばれる
    def postcmd(self, stop, line):
        logger.debug(f"--- [POST] '{line}' の実行が終わりました ---")
        self.code_buffer = "" # 後処理
        return stop

    def emptyline(self):
        # 何もしないように上書き（これがないと直前のコマンドが走る）
        logger.debug("emptyline")
        #pass

    def reset_observation_environment(self):
        # TODO - なぜこの場所にTimeのリセットがあるのか？ とりあえず無効化
        #self.interp.config.env['Time'] = self.interp.config.SSOEphem("now")
        self.interp.var_mgr.observer = {}

    def default(self, line):
        logger.debug(f"default: line={line}")
        if not line.strip():
            return
        try:
            log_mode = self.interp.config.env["Log"].strip('"')

            if log_mode == "Yes":
                logging.getLogger().setLevel(logging.DEBUG)
                #logging.disable(logging.NOTSET)
            elif log_mode == "No":
                logging.getLogger().setLevel(logging.CRITICAL)
                #logging.disable(logging.CRITICAL)
            else:
                level = getattr(logging, log_mode, logging.CRITICAL)
                logging.disable(level)

            # 観測環境をリセット（観測日時、Bodyの観測日指定）
            self.reset_observation_environment()

            # パースを実行（末尾に改行を付けて文末を認識させる）
            #tree = self.parser.parse(line + "\n")
            tree = self.parser.parse(self.code_buffer)
            self.code_buffer = ""

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
                logger.debug(f"res:{res}")
                # Token(改行等)は無視
                if isinstance(res, Token):
                    continue

                # リストが入れ子（ネスト）になっている場合を想定して再帰的に処理
                if isinstance(res, list):
                    for sub_res in res:
                        if not isinstance(sub_res, Token) and sub_res is not None:
                            if self.interp.config.env["Echo"] == "Yes":
                                logger.debug(f"sub_res:{sub_res}")
                                console.print(sub_res)
                else:
                    # 通常の出力
                    if res is not None and (self.interp.config.env["Echo"] == "Yes"):
                        logger.debug(f"return type: {type(res)}")
                        match res:
                            case ephem.Date():
                                # <class 'ephem.Date'> なら Tz を加算する
                                date_str=f"{self.interp.config.fromUTC(res)}"
                                base_part = date_str[:19]
                                tz_part = date_str[20:]
                                dt = datetime.strptime(base_part, "%Y/%m/%d %H:%M:%S")
                                weekday = dt.strftime("%a").upper()
                                formatted_str = f"{date_str[:10]} ({weekday}) {date_str[10:]}"
                                console.print(formatted_str)
                            case float() | str() | int():
                                console.print(res)
                            case ephem.Observer():
                                console.print(f"観測地オブジェクト:")
                                console.print(f"date={self.interp.config.fromUTC(res.date)}  緯度={res.lat}  経度={res.lon}  標高={res.elevation:.1f}")
                            case ephem.Body():
                                console.print(f"天体オブジェクト:\n{res}")
                            case _:
                                logger.debug(res)
                                pass

        except UnexpectedToken as e:
            if e.token.type == '$END':
                # 入力がまだ途中の場合（if文の途中など）は、次の行を待つ
                # continue
                pass
            else:
                # 本当の文法エラーの場合は表示してバッファをリセット
                print(f"Syntax Error: {e}")
                self.code_buffer = ""

        except UnexpectedEOF:
            # Larkのバージョンや設定によっては UnexpectedEOF が発生する
            # こちらもキャッチして継続
            # continue
            pass

        except Exception as e:
            print(f"Error: {e}")
            self.code_buffer = ""

    # --- シェル制御コマンド ---
    def do_shell(self, line):
        """! <command> : OSのシェルコマンドを実行する"""
        if not line:
            console.print("コマンドを入力してください")
            return

        # os.system を使用して、入力されたコマンドを直接実行
        os.system(line)
        self.code_buffer=""

    def do_hello(self, arg):
        self.code_buffer =""
        print(f"Hello {arg}!")

    def do_exit(self, arg):
        console.print("""SSOを終了します""")
        return True # Trueを返すとループが終了する

    def do_quit(self, arg):
        """終了コマンド"""
        return True

    # EOF (Ctrl+D) での終了対応
    def do_EOF(self, arg):
        print()
        return True

    def do_help(self, arg):
        """
        help と打つとコマンド一覧、help [コマンド名] で詳細を表示します。
        コマンド名は、先頭文字を入力してTabキーを押すと補完機能が働きます。
        """
        """help [コマンド名]\nヘルプを表示します。"""
        # 引数がない（単に help と打たれた）場合
        if not arg:
            print("\n" + "="*30)
            print("【コマンド入力形式のガイド】")
            print("  代入 : 変数 = コマンド名(引数)")
            print("  観測 : 観測地 -> 天体名")
            print("  月食 : Sun -> 観測地 -> Moon")
            print("")
            print("＊観測の前に変数Timeに観測したい時刻を入力します。")
            print("＊方法は”help Time”を参照してください。")
            print("＊Timeには、あらかじめSSO起動時の時刻が入ってます。")
            print("＊観測地にHereを指定すると、構成情報config.iniで設定した現在地が使われます。")
            print("＊コマンド名や天体名はTabキーで文字入力補完機能が使えます。")

            print("  - 終了するには 'exit' または 'quit' と入力してください。")
            print("="*30 + "\n")
            input("Returnキーを押してください")

        # 親クラスの help 処理をそのまま呼び出す
        res = cmd.Cmd.do_help(self, arg)
        self.code_buffer = "" # 後処理
        return res

    def help_Body(self):
        planets =  [name for _0, _1, name in ephem._libastro.builtin_planets()]

        print(Body_help.get("Body"))
        print(" ".join(planets))

    def print_topics(self, header, cmds, cmdlen, maxcol):
        if cmds:
            self.stdout.write("%s\n" % str(header))
            if self.ruler:
                # 日本語の幅（全角2, 半角1）を計算して下線を引く
                header_width = sum([(2 if unicodedata.east_asian_width(c) in 'FWA' else 1) for c in header])
                self.stdout.write("%s\n" % (self.ruler * header_width))
            self.columnize(cmds, maxcol)
            self.stdout.write("\n")


if __name__ == "__main__":
    try:
        SSOShell().cmdloop()
    except KeyboardInterrupt:
        # Ctrl+C での強制終了をきれいに処理
        print("\nGoodbye.")
