from lark import Lark, Transformer

# 文法定義
grammar = """
    ?start: sum
    ?sum: product
        | sum "+" product   -> add
        | sum "-" product   -> subtract
    ?product: atom
        | product "*" atom  -> multiply
        | product "/" atom  -> divide
    ?atom: NUMBER           -> number
        | "-" atom          -> negative
        | "(" sum ")"
    %import common.NUMBER
    %import common.WS
    %ignore WS
"""

class CalculateTree(Transformer):
    def number(self, n):
        return float(n[0])
    
    def negative(self, n):
        return -n[0]
    
    def add(self, args):
        return args[0] + args[1]
    
    def subtract(self, args):
        return args[0] - args[1]
    
    def multiply(self, args):
        return args[0] * args[1]
    
    def divide(self, args):
        return args[0] / args[1]

# パーサーの作成
parser = Lark(grammar, parser='lalr', transformer=CalculateTree())

# 計算機能の実装
def calculate(expression):
    try:
        return parser.parse(expression)
    except Exception as e:
        return f"エラー: {str(e)}"

# 使用例
if __name__ == "__main__":
    while True:
        expr = input("計算式を入力してください（終了する場合は 'q' を入力）: ")
        if expr.lower() == 'q':
            break
        result = calculate(expr)
        print(f"結果: {result}")

