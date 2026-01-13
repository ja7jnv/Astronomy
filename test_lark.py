from lark import Lark

# いただいた文法定義（example.larkの中身）
grammar = r"""
?program: [(state)+]

// statement
?state: expr ";"
      | function
      | assignment ";"
      | return_state ";"

function: "def" new_symbol "(" [parameter ("," parameter)*] ")" "{" program "}"
assignment: new_symbol "=" expr
return_state: "return" expr

// expression
?expr: term
     | addition
     | substraction
     | function_call

addition: expr "+" term
substraction: expr "-" term
function_call: symbol "[" [expr ("," expr)*] "]"

?term: fact
     | multiplication
     | division

multiplication: term "*" fact
division: term "/" fact

?fact: number
     | symbol
     | priority

?priority: "(" expr ")"
symbol: WORD
number: SIGNED_NUMBER

new_symbol: WORD
parameter: WORD

%import common.WORD
%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
"""

# パーサの生成（Lex-Yacc経験者には馴染み深い 'lalr' アルゴリズムを指定）
parser = Lark(grammar, start='program', parser='lalr')

# テストするソースコード
# 単純な代入と、優先順位のある計算式
source_code = "result = 1 + 2 * 3;"

# パース実行
tree = parser.parse(source_code)

# 構文木の表示
print("=== 構文木 (Tree) ===")
print(tree.pretty())
