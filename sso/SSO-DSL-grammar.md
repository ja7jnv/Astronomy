# SSO DSL 文法リファレンス（自動生成版）

この文書は `sso.lark` の内容から自動生成された文法リファレンスです。

## メタディレクティブ

```lark
%import common.WS_INLINE
%ignore WS_INLINE
%import common.NEWLINE
%ignore COMMENT
```

## 構文ルール

### ?arrow

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?arrow: sum | arrow "->" sum -> arrow_op
```

### ?atom

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?atom: number
     | STRING           -> string_literal
	 | FSTRING          -> f_string
     | funccall
     | auxcall
     | VAR_NAME         -> var_load
     | BODY_NAME        -> body_load
     | "(" expr ")"
     | dot_access
```

### ?comparison

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?comparison: arrow COMPARISON_OP arrow -> compare_op
           | arrow
```

### ?expr

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?expr: logical_or
```

### ?logical_and

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?logical_and: logical_not
            | logical_and AND_OP logical_not -> and_and
```

### ?logical_not

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?logical_not: NOT_OP logical_not -> not_op
            | comparison
```

### ?logical_or

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?logical_or: logical_and
           | logical_or OR_OP logical_and  -> or_op
```

### ?number

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?number: FLOAT -> float_num
       | INT   -> int_num
```

### ?power

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?power: atom | atom "^" power -> pow
```

### ?product

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?product: power
        | product "*" power -> mul
		| product "/" power -> div
		| product "%" power -> mod
```

### ?statement

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?statement: (assignment
          | expr
		  | if_stmt
		  | for_stmt
		  | while_stmt
		  | def_stmt
		  | import_stmt
		  | return_stmt) (";" | NEWLINE)
          | NEWLINE
          | "break"     -> break_stmt
          | "continue"  -> continue_stmt
```

### ?sum

（説明文は未作成です。interpreter の実装を参照してください。）

```lark
?sum: product | sum "+" product -> add | sum "-" product -> sub
```

### arglist

関数呼び出し・補助呼び出しで使う引数リストです。

```lark
arglist: expr ("," expr)*
```

### argparm

関数定義で使う仮引数リストです。

```lark
argparm: VAR_NAME ("," VAR_NAME)*
```

### assignment

変数または Body への代入文。`x = expr` や `Moon = expr` など。

```lark
assignment: VAR_NAME "=" expr   -> assign_var
          | BODY_NAME "=" expr  -> assign_body
```

### auxcall

`Name[expr, ...]` 形式の補助呼び出しです。観測用の日付や場所など、Body に付随する追加情報の設定に使われます。

```lark
auxcall: (BODY_NAME | VAR_NAME) "[" [arglist] "]"
```

### block

1 個以上の statement で構成されるブロックです。if/for/while/def などの内部で利用されます。

```lark
block: statement+
```

### def_stmt

ユーザ定義関数を定義します。`def Name(x, y) do ... end_def` 形式です。

```lark
def_stmt: "def" (BODY_NAME | VAR_NAME) "(" [argparm] ")" "do" block "end_def"
```

### dot_access

`var.attr` 形式で Python オブジェクトの属性にアクセスします。

```lark
dot_access: VAR_NAME "." VAR_NAME
          | dot_access "." VAR_NAME
```

### for_stmt

`for VAR in expr do ... end_for` 形式の for ループです。expr の評価結果（リストや range など）を順に走査します。

```lark
for_stmt: "for" VAR_NAME "in" expr "do" block "end_for"
```

### funccall

`Name(expr, ...)` 形式の関数呼び出しです。組み込み関数、SSO 独自関数、ユーザ定義関数が対象となります。

```lark
funccall: (BODY_NAME | VAR_NAME) "(" [arglist] ")"
```

### if_stmt

条件分岐構文 `if expr then ... [else ...] end_if` を表します。

```lark
if_stmt: "if" expr "then" block ["else" block] "end_if"
```

### import_stmt

外部スクリプトファイルを読み込み、その中の定義を現在の環境に取り込みます。

```lark
import_stmt: "import" STRING
```

### return_stmt

関数から値を返します。`return expr`。

```lark
return_stmt: "return" [expr]
```

### start

プログラム全体。1 行以上の statement から構成されます。

```lark
start: statement*
```

### while_stmt

`while expr do ... end_while` 形式の while ループです。expr が真である間、ブロックを繰り返し実行します。

```lark
while_stmt: "while" expr "do" block "end_while"
```

## トークン（終端記号）

### AND_OP

（説明文は未作成です。正規表現を参照してください。）

```lark
AND_OP: "AND"
```

### BODY_NAME

Body 名・観測点名など。先頭大文字、以後英数字とアンダースコア。

```lark
BODY_NAME: /[A-Z][a-zA-Z0-9_]*/
```

### COMMENT

`//` から行末までのコメントです。

```lark
COMMENT: "//" /[^\n]/*
```

### COMPARISON_OP

（説明文は未作成です。正規表現を参照してください。）

```lark
COMPARISON_OP: ">" | "<" | "==" | "!="
```

### FLOAT

浮動小数点数。負号付きも可（例: -12.34）。

```lark
FLOAT: /-?\d+\.\d+/
```

### FSTRING.2

（説明文は未作成です。正規表現を参照してください。）

```lark
FSTRING.2: /f"[^"]*"/           // FSTRING の優先度を高く設定 (.2)
```

### INT

整数。負号付きも可（例: -10）。

```lark
INT: /-?\d+/
```

### NOT_OP

（説明文は未作成です。正規表現を参照してください。）

```lark
NOT_OP: "NOT"
```

### OR_OP

（説明文は未作成です。正規表現を参照してください。）

```lark
OR_OP: "OR"
```

### STRING

文字列リテラル。"..." または '...' で囲まれた範囲。

```lark
STRING: /"[^"]*"/ | /'[^']*'/
```

### VAR_NAME

変数名。先頭小文字、以後英数字とアンダースコア。

```lark
VAR_NAME: /[a-z][a-zA-Z0-9_]*/
```
