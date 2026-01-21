# interpreter.py
from lark import Lark, Transformer, v_args
from classes import SSOObserver, SSOMountain, SSOTime, SSONumber, SSOCalculator, DEFAULT_TZ

class SSOInterpreter(Transformer):
    def __init__(self):
        self.variables = {"Tz": SSONumber(DEFAULT_TZ)} # 
        self.objects = {}
        self.echo = True # 

    @v_args(inline=True)
    def assign_var(self, name, value):
        if name == "Echo": #  Echo制御
            self.echo = (str(value) != "Off")
            return None
        if name == "Tz":
            self.variables["Tz"] = value
        else:
            self.variables[str(name)] = value
        return value

    @v_args(inline=True)
    def assign_obj(self, name, value):
        if hasattr(value, 'name'):
            value.name = str(name)
        self.objects[str(name)] = value
        return value

    @v_args(inline=True)
    def arrow_op(self, left, right):
        """
        Arrow演算子のロジック [cite: 2, 3]
        Context Chain: Observer -> [Modifier] -> Target
        """
        # Case 1: Observer -> Body (Moon, Sun etc.)
        if isinstance(left, SSOObserver) and isinstance(right, str):
            # rightが予約語(天体名)の場合
            return SSOCalculator.observe(left, right)

        # Case 2: Observer -> Time/Modifier -> ...
        # Rise, Set, Zenith などの予約語処理はここで行う中間オブジェクトが必要
        # 簡易的にタプルで (Observer, Mode) を返す設計にします
        if isinstance(left, SSOObserver) and right in ["Rise", "Set", "Zenith"]:
            return (left, right)
        
        # Case 3: (Observer, Mode) -> Body
        if isinstance(left, tuple) and isinstance(right, str):
            obs, mode = left
            return SSOCalculator.observe(obs, right, mode=mode)

        # Case 4: Observer -> Mountain -> Body (Chain 1)
        if isinstance(left, SSOObserver) and isinstance(right, SSOMountain):
            return (left, "Mountain", right) # (Obs, Mode, Context)

        # Case 5: (Obs, "Mountain", MtnObj) -> Body
        if isinstance(left, tuple) and len(left) == 3 and isinstance(right, str):
            obs, mode, ctx = left
            return SSOCalculator.observe(obs, right, mode=mode, context_obj=ctx)
        
        # 関数呼び出し結果(Time)を使った観測: Yuzawa -> Moon(Now)
        # 文法上、Moon(Now) は funccall として処理され、結果が渡ってくる
        # ここでは簡易化のため、右辺が天体名文字列でない場合の処理を追加
        return f"Operation not supported: {left} -> {right}"

    @v_args(inline=True)
    def number(self, n):
        return SSONumber(n)

    @v_args(inline=True)
    def string_literal(self, s):
        # 前後のクォートを除去して返す ("xxxx" -> xxxx)
        return s[1:-1]

    @v_args(inline=True)
    def var_load(self, name):
        return self.variables.get(str(name), SSONumber(0))

    @v_args(inline=True)
    def obj_load(self, name):
        name = str(name)
        # 予約語(クラスファクトリや定数)の解決
        if name in ["Date", "Now", "Observer", "Mountain", "Rise", "Set", "Zenith", "Off", "On"]:
            return name # 識別子として返す
        # 登録済みオブジェクト
        if name in self.objects:
            return self.objects[name]
        # 天体名としてそのまま返す
        return name

    def funccall(self, items):
        func_name = items[0]
        args = items[1].children if len(items) > 1 and items[1] else []
        
        # 値のアンラップ
        clean_args = []
        for a in args:
            if isinstance(a, SSONumber): clean_args.append(a.value)
            elif isinstance(a, SSOTime): clean_args.append(a)
            else: clean_args.append(a)

        if func_name == "Date":
            # 引数処理 (2026/1/21...) は文字列として渡されるか、除算として計算される可能性がある
            # 文法上、2026/1/21 は (2026/1)/21 と計算されるため、工夫が必要
            # ここでは簡略化のため、文字列パースではなく数値引数 (y, m, d, h, m, s) を想定するか
            # プロンプトの例にある '/' 区切りに対応するには字句解析器の調整が必要。
            # プロトタイプとして、引数が3つなら日付とみなす
            if len(clean_args) >= 3:
                return SSOTime(f"{int(clean_args[0])}/{int(clean_args[1])}/{int(clean_args[2])}")
            return SSOTime()

        if func_name == "Now":
            return SSOTime()

        if func_name == "Observer":
            return SSOObserver(*clean_args)
        
        if func_name == "Mountain":
            return SSOMountain(*clean_args)

        return f"Unknown function: {func_name}"

    # 四則演算等の実装 (省略可だが基本のみ実装)
    @v_args(inline=True)
    def add(self, a, b): return SSONumber(a.value + b.value)
    # ... 他の演算も同様に SSONumber を返す
