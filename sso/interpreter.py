from lark.visitors import Interpreter
from lark import Token
from classes import SSOObserver, SSOCalculator, SSOSystemConfig
from datetime import datetime, timezone
import numpy as np
import configparser
import ephem    # 型を参照するためにインポート（実際の計算はSSOSystemConfig経由で行う）

import logging # ログの設定
logging.basicConfig(
level=logging.DEBUG, # 出力レベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger =  logging.getLogger(__name__)

class SSOInterpreter(Interpreter):
    def __init__(self):
        self.variables = {}
        self.body = {}

        self.config = SSOSystemConfig() # 環境変数 etc.
        self.ini = configparser.ConfigParser()
        self.ini.read('config.ini', encoding='utf-8')
        lat = self.ini['Here']['lat']
        lon = self.ini['Here']['lon']
        elev = self.ini['Here']['elev']
        setattr(self.config.env['Here'], "lat", lat)
        setattr(self.config.env['Here'], "lon", lon)
        setattr(self.config.env['Here'], "elevation", float(elev))
        self.config.env['Tz']   = float(self.ini['ENV']['Tz'])
        self.config.env['Log']  = self.ini['ENV']['Log'].strip('"')
        self.config.env['Echo'] = self.ini['ENV']['Echo'].strip('"')

    # --- 代入系 ---
    def assign_var(self, tree):
        # assignment: VAR_NAME "=" expr
        name = tree.children[0].value # Tokenから文字列取得
        expr = self.visit(tree.children[1]) # 右辺を評価
        
        self.variables[name] = expr
        value = self.config.reformat(expr) or expr
        return f"{name}: {value}"

    def assign_body(self, tree):
        # assignment: BODY_NAME "=" expr
        name = tree.children[0].value
        value = self.visit(tree.children[1])

        # 以下のbody操作はConfigオブジェクトへの操作として処理
        if name in self.config.env.keys():
            method_name = f"set_{name}"
            method = getattr(self.config, method_name)
            return method(value)

        self.body[name] = value

        # Observer もしくは天体ならフォーマット
        value = self.config.reformat(value)
        return f"{name}: {value}"

    # --- 演算系 ---

    def arrow_op(self, tree):
        logger.debug(tree.pretty())
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        logger.debug(f"\nleft:{left}\nright:{right}")

        obs = left[0] if isinstance(left, tuple) else left
        mode = left[1] if isinstance(left, tuple) else "Now"
        target = right
        logger.debug(f"\nobs:{obs}\nmode:{mode}\ntarget:{target}")

        if isinstance(obs, ephem.Observer):
            # ユーザーが明示的に時刻変数を設定しているかチェック
            # Time という変数があればそれを使う
            logger.debug(f"Observer date set to: {obs.date}")
            obs.date = str(self.config.env.get("Time"))

        # 1. Observer -> Target (Body)
        if isinstance(obs, ephem.Observer) and isinstance(target, ephem.Body) and mode == "Now":
            logger.debug(f"Observer -> Target (Body)")
            target.compute(obs)
            alt = np.rad2deg(target.alt)
            az = np.rad2deg(target.az)
            value = self.config.reformat(obs, target)
            return value

        # 2. Observer -> Mode (Rise, Set)
        if isinstance(left, SSOObserver) and right in ["Rise", "Set"]:
            logger.debug(f"pattern 1 Observer -> Mode (Rise, Set)")
            return (left, right)

        # 3. (Observer, Mode) -> Target (Moon)
        if isinstance(left, tuple) and isinstance(right, str):
            obs, mode = left
            logger.debug(f"pattern 2 (Observer, Mode) -> Target (Moon)")
            return SSOCalculator.observe(obs, right, self.config, mode=mode)
        
        return f"Error: Invalid arrow operation {left} -> {right}"

    ###

    def add(self, tree): return self.visit(tree.children[0]) + self.visit(tree.children[1])
    def sub(self, tree): return self.visit(tree.children[0]) - self.visit(tree.children[1])
    def mul(self, tree): return self.visit(tree.children[0]) * self.visit(tree.children[1])
    def div(self, tree): return self.visit(tree.children[0]) / self.visit(tree.children[1])
    def pow(self, tree): return self.visit(tree.children[0]) ** self.visit(tree.children[1])

    # --- プリミティブ・変数参照 ---
    def number(self, tree):
        # number: NUMBER
        return float(tree.children[0].value)

    def string_literal(self, tree):
        # 文字列 "..." の中身を取り出す
        return tree.children[0].value[1:-1]

    def var_load(self, tree):
        name = tree.children[0].value
        return self.variables.get(name, 0.0)

    def var_name(self, tree):
        loggere.degug(tree)
        name = tree.children[0].value
        return f"{name}"

    # --- var.attr 呼び出し ---
    def dot_access(self, tree):
        name = tree.children[0].value
        attr = tree.children[1].value

        var = self.variables.get(name, 0.0)
        value = getattr(var, attr, 0)
        logger.debug(f"{name}.{attr} = {value}")
        return value


    def body_load(self, tree):
        name = tree.children[0].value

        # 内部config変数
        if name in self.config.env.keys():
            value =  self.config.env[name]

        # 今はNowだけだからよいが増えてきたら美しい方法で！！
        elif name == "Now":
            # 引数なしで現在時刻を返す
            value =  self.config.SSOEphem("now")

        # 未登録オブジェクト
        elif name not in self.body.keys():
            value = self.config.SSOEphem(name)
            self.body[name] = value

        # 登録済みオブジェクト
        else:
            value =  self.body.get(name, name)

        return value
 

    # --- 関数呼び出し ---
    def funccall(self, tree):
        # funccall: BODY_NAME | VAR_NAME "(" [arglist] ")"
        # 基本的にephem.funccall(...) にする。
        # Dateは時差が加算されているのでUTCに変換してfunccallする。
        # Mountain等のDSL固有要素はこの関数内で呼び出しクラスを振り分ける。
        attr = tree.children[0].value
        logger.debug(f"body(): name={attr}")
        
        # 引数の処理
        args = []
        # tree.children[1] が存在し、かつそれが Token (")") ではなく 
        # 文法上の arglist ノードである場合のみ visit する
        if len(tree.children) > 1:
            child = tree.children[1]
            # LarkのInterpreterでは、省略可能な [arglist] が無い場合、
            # その位置には None や 閉じカッコの Token が入ることがある
            if hasattr(child, 'data'): # ノード(Tree)であることを確認
                args = self.visit(child)

        # 関数ごとの処理

        if attr == "Date":
            d_str = args[0] if args else None
            utc_dt = self.config.toUTC(d_str)
            return self.config.SSOEphem(attr, utc_dt)
        
        if attr == "Now":
            # 引数なしで現在時刻を返す
            return self.config.SSOEphem("now")

        if (attr == "Observer") | (attr == "Mountain"):
            logger.debug(f"{attr} command: args={args}")
            
            if not args:
                # 対話入力モード
                try:
                    lat = float(input("... 緯度 = "))
                    lon = float(input("... 経度 = "))
                    elev = float(input("... 標高 = "))
                except (ValueError, EOFError, KeyboardInterrupt):
                    lat = 0
                    lon = 0
                    elev = 0
                location = SSOObserver(attr, lat, lon, elev, config=self.config)
            else:
                location = SSOObserver(attr, *args, config=self.config)

            return location.ephem_obs

        logger.debug(f"Fundamental ephem call: arrt={attr}, args={args}")
        return self.config.SSOEphem(attr, *args, config=self.config)

    # ---  ---

    def arglist(self, tree):
        # 引数リストを評価してPythonのリストとして返す
        return [self.visit(child) for child in tree.children]

    def start(self, tree):
        # 親の start ノードでリストを返さず、
        # 子要素(statement)を一つずつ visit して、その結果をそのまま返す
        last_result = None
        for child in tree.children:
            res = self.visit(child)
            if not isinstance(res, Token):
                last_result = res
        return last_result # 最後の実行結果だけを返す
