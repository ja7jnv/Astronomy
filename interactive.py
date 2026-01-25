from lark import Lark

# 文法の定義（LALRパーサーを使用する必要がある）
parser = Lark(r"""
    ?start: "move" DIRECTION | "quit"
    DIRECTION: "up" | "down" | "left" | "right"
    %import common.WS
    %ignore WS
""", parser='lalr')

# 対話型パースの開始
interactive = parser.parse_interactive("move ")
interactive.exhaust_lexer()

# 次に入力可能なトークンを表示
print(interactive.accepts())  # {'DIRECTION'} が返る

