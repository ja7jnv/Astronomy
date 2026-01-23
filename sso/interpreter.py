from lark.visitors import Interpreter
from lark import Token
from classes import SSOObserver, SSOMountain, SSOTime, SSOCalculator, SSOSystemConfig

class SSOInterpreter(Interpreter):
    def __init__(self):
        self.variables = {}
        self.objects = {}
        self.config = SSOSystemConfig() # Tz, Echoなどを管理

    # --- 代入系 ---
    def assign_var(self, tree):
        # assignment: VAR_NAME "=" expr
        name = tree.children[0].value # Tokenから文字列取得
        value = self.visit(tree.children[1]) # 右辺を評価
        
        self.variables[name] = value
        return f"{name}: {value}"

    def assign_obj(self, tree):
        # assignment: OBJ_NAME "=" expr
        name = tree.children[0].value
        value = self.visit(tree.children[1])

        # Tz, Echo は Configオブジェクトへの操作として処理
        if name == "Tz":
            return self.config.set_tz(value)
        if name == "Echo":
            return self.config.set_echo(value)

        # 通常オブジェクト
        if hasattr(value, 'name'):
            value.name = name
        self.objects[name] = value
        
        # オブジェクトそのものを返す（REPL表示用）
        return value

    # --- 演算系 ---

    def arrow_op(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])

        obs = left[0] if isinstance(left, tuple) else left
        #print(f"**debug**\n{obs}\n**debug_end**")
        mode = left[1] if isinstance(left, tuple) else "Now"
        target = right

        if isinstance(obs, SSOObserver):
            # 1. ユーザーが明示的に時刻変数を設定しているかチェック
            # DateTime または Time という変数があればそれを使う
            target_time = self.variables.get("DateTime") or self.variables.get("Time")
            obs.set_time(target_time)

        # 1. Observer -> Mode (Rise, Set)
        if isinstance(left, SSOObserver) and right in ["Rise", "Set"]:
            return (left, right)

        # 2. (Observer, Mode) -> Target (Moon)
        if isinstance(left, tuple) and isinstance(right, str):
            obs, mode = left
            return SSOCalculator.observe(obs, right, self.config, mode=mode)
        
        # 3. Observer -> Target (Moon)
        if isinstance(left, SSOObserver) and isinstance(right, str):
            return SSOCalculator.observe(left, right, self.config)

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

    def obj_load(self, tree):
        name = tree.children[0].value
        # 予約語的なオブジェクト名
        if name in ["Rise", "Set", "Moon", "Sun", "Mars", "Jupiter", "Venus", "Saturn"]:
            return name
        # 登録済みオブジェクト
        return self.objects.get(name, name)

    # --- 関数呼び出し ---

    def funccall(self, tree):
        # funccall: OBJ_NAME "(" [arglist] ")"
        func_name = tree.children[0].value
        
        # 引数の処理
        args = []
        # tree.children[1] が存在し、かつそれが Token (")") ではなく 
        # 文法上の arglist ノードである場合のみ visit する
        if len(tree.children) > 1:
            child = tree.children[1]
            # LarkのInterpreterでは、省略可能な [arglist] が無い場合、
            # その位置には None や 閉じカッコの Token が入ることがあります
            if hasattr(child, 'data'): # ノード(Tree)であることを確認
                args = self.visit(child)

        # 関数ごとの処理
        if func_name == "Date":
            d_str = args[0] if args else None
            print(f"**debug**\n{d_str}\n**debug_end**")
            return SSOTime(d_str, config=self.config)
        
        if func_name == "Now":
            # 引数なしで現在時刻を返す
            return SSOTime(None, config=self.config)

        if func_name == "Observer":
            if not args:
                # 対話入力モード
                try:
                    lat = float(input("... 緯度 = "))
                    lon = float(input("... 経度 = "))
                    elev = float(input("... 標高 = "))
                    return SSOObserver(lat, lon, elev)
                except (ValueError, EOFError, KeyboardInterrupt):
                    return SSOObserver(0, 0, 0)
            return SSOObserver(*args)

        return f"Unknown function: {func_name}"

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
