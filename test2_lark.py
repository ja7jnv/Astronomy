from lark import Lark, Transformer, v_args
EXAMPLE = 'example.lark'

grammar = open(EXAMPLE).read()

# --------------------------------------------------------
# 1. インタプリタ本体 (Transformer)
# --------------------------------------------------------
@v_args(inline=True)  # 子要素をリストではなく、引数としてバラして受け取る設定
class MyInterpreter(Transformer):
    def __init__(self):
        self.variables = {}  # 変数を格納するメモリ

    # 数値の変換
    def number(self, n):
        return float(n)

    # 変数の参照
    def symbol(self, s):
        return self.variables.get(s, 0)

    # 計算（四則演算）
    def addition(self, left, right):
        return left + right

    def multiplication(self, left, right):
        return left * right

    # 代入文
    def assignment(self, name, value):
        # new_symbol から文字列を取り出して変数に格納
        var_name = str(name)
        self.variables[var_name] = value
        print(f"DEBUG: {var_name} に {value} を代入しました")
        return value

    # 変数名（new_symbol）
    def new_symbol(self, s):
        return str(s)

    # 文のリスト（program）
    def program(self, *states):
        return states[-1] if states else None

# --------------------------------------------------------
# 2. 実行
# --------------------------------------------------------
parser = Lark(grammar, start='program', parser='lalr')
interpreter = MyInterpreter()

source = """
a = 5;
b = 3;
c = 6;

result = a + b * c;
"""

tree = parser.parse(source)
final_result = interpreter.transform(tree)

print(f"\n最終結果 (result): {interpreter.variables['result']}")
