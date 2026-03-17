#!/usr/bin/env python3
"""
SSO DSL 文法書自動生成スクリプト（初期版）

- sso.lark から BNF 風の構文一覧を生成
- 代表的なルールには手書きの日本語説明を付与
- Markdown を stdout またはファイルに出力
"""

from pathlib import Path
from textwrap import indent

GRAMMAR_FILE = Path("sso.lark")
OUTPUT_FILE = Path("SSO-DSL-grammar.md")


def load_grammar(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines = [ln.rstrip() for ln in text.splitlines()]
    return lines


def split_rules(lines: list[str]):
    """
    .lark をかなり素朴に
    - 非終端ルール
    - 終端ルール
    - %import / %ignore / コメント
    に分ける。
    """
    nonterminals: dict[str, list[str]] = {}
    terminals: dict[str, str] = {}
    meta: list[str] = []

    current_rule = None
    current_lines: list[str] = []

    def flush_rule():
        nonlocal current_rule, current_lines
        if current_rule is None:
            return
        body = "\n".join(current_lines).strip()
        if body:
            nonterminals[current_rule] = current_lines.copy()
        current_rule = None
        current_lines = []

    for ln in lines:
        stripped = ln.strip()
        if not stripped or stripped.startswith("//"):
            continue

        # メタ行
        if stripped.startswith("%"):
            meta.append(ln)
            continue

        # 端末定義 (NAME: regex ...)
        if ":" in stripped and not stripped.startswith("?") and not stripped.startswith("start"):
            # ただし非終端も ":" を使うので、先に '?start' 等を除外している
            name, rest = stripped.split(":", 1)
            name = name.strip()
            if name.isupper():
                terminals[name] = rest.strip()
                continue

        # ここから非終端ルール検出（start / ?expr / if_stmt など）
        # 先頭に '?' が付く Lark の「エイリアス非終端」もまとめて扱う
        if not ln.startswith(" ") and not ln.startswith("\t"):
            # 新しいルールの開始候補
            # 例: "start: statement*"
            if ":" in stripped:
                flush_rule()
                head, rest = stripped.split(":", 1)
                current_rule = head.strip()
                current_lines = [ln]
            else:
                # よくわからない行はそのまま流す
                flush_rule()
        else:
            # 継続行
            if current_rule is not None:
                current_lines.append(ln)

    flush_rule()
    return nonterminals, terminals, meta


# 代表的なルールの説明（手書き）
RULE_DOCS = {
    "start": "プログラム全体。1 行以上の statement から構成されます。",
    "statement": "1 行の文。代入、式評価、if/for/while/def/import/return などを含みます。末尾にセミコロンまたは改行を取ります。",
    "expr": "式の総称。論理演算・比較演算・算術演算・矢印演算などを含みます。",
    "if_stmt": "条件分岐構文 `if expr then ... [else ...] end_if` を表します。",
    "for_stmt": "`for VAR in expr do ... end_for` 形式の for ループです。expr の評価結果（リストや range など）を順に走査します。",
    "while_stmt": "`while expr do ... end_while` 形式の while ループです。expr が真である間、ブロックを繰り返し実行します。",
    "def_stmt": "ユーザ定義関数を定義します。`def Name(x, y) do ... end_def` 形式です。",
    "return_stmt": "関数から値を返します。`return expr`。",
    "import_stmt": "外部スクリプトファイルを読み込み、その中の定義を現在の環境に取り込みます。",
    "block": "1 個以上の statement で構成されるブロックです。if/for/while/def などの内部で利用されます。",
    "logical_or": "`A OR B` のような論理和を表します。OR より優先順位の高い AND/NOT/比較などに基づいて評価されます。",
    "logical_and": "`A AND B` のような論理積を表します。",
    "logical_not": "`NOT A` のような否定を表します。",
    "comparison": "`A > B` `A == B` などの比較演算を表します。",
    "arrow": "矢印演算子 `->`。`Observer -> Body` などの形で、天体観測・距離計算・食の計算などを行います。",
    "sum": "加算・減算 (`+`, `-`) を表すレベルの式です。",
    "product": "乗算・除算・剰余 (`*`, `/`, `%`) を表すレベルの式です。",
    "power": "冪乗 (`^`) を表すレベルの式です。",
    "atom": "数値リテラル、文字列、関数呼び出し、Body/変数参照、括弧式などの最小単位です。",
    "assignment": "変数または Body への代入文。`x = expr` や `Moon = expr` など。",
    "dot_access": "`var.attr` 形式で Python オブジェクトの属性にアクセスします。",
    "funccall": "`Name(expr, ...)` 形式の関数呼び出しです。組み込み関数、SSO 独自関数、ユーザ定義関数が対象となります。",
    "auxcall": "`Name[expr, ...]` 形式の補助呼び出しです。観測用の日付や場所など、Body に付随する追加情報の設定に使われます。",
    "arglist": "関数呼び出し・補助呼び出しで使う引数リストです。",
    "argparm": "関数定義で使う仮引数リストです。",
    "number": "INT または FLOAT の数値リテラルを表します。",
}


# 終端の説明（簡易版）
TERMINAL_DOCS = {
    "VAR_NAME": "変数名。先頭小文字、以後英数字とアンダースコア。",
    "BODY_NAME": "Body 名・観測点名など。先頭大文字、以後英数字とアンダースコア。",
    "STRING": "文字列リテラル。\"...\" または '...' で囲まれた範囲。",
    "FSTRING": "f 文字列。f\"高度={alt:5.2f}\" のように、{} 内を変数展開します。",
    "FLOAT": "浮動小数点数。負号付きも可（例: -12.34）。",
    "INT": "整数。負号付きも可（例: -10）。",
    "NEWLINE": "改行。文の終端として扱われます。",
    "COMMENT": "`//` から行末までのコメントです。",
    "WS_INLINE": "行内の空白（タブ・スペース）。無視されます。",
}


def format_rule_md(name: str, lines: list[str]) -> str:
    head = f"### {name}\n"
    doc = RULE_DOCS.get(name, "（説明文は未作成です。interpreter の実装を参照してください。）")
    body = "```lark\n" + "\n".join(lines) + "\n```"
    return f"{head}\n{doc}\n\n{body}\n"


def format_terminal_md(name: str, body: str) -> str:
    head = f"### {name}\n"
    doc = TERMINAL_DOCS.get(name, "（説明文は未作成です。正規表現を参照してください。）")
    return f"{head}\n{doc}\n\n```lark\n{name}: {body}\n```\n"


def build_markdown(nonterminals, terminals, meta) -> str:
    parts: list[str] = []

    # 1. タイトル・概要
    parts.append("# SSO DSL 文法リファレンス（自動生成版）\n")
    parts.append("この文書は `sso.lark` の内容から自動生成された文法リファレンスです。\n")

    # 2. メタディレクティブ（%import, %ignore など）の抜粋
    if meta:
        parts.append("## メタディレクティブ\n")
        parts.append("```lark")
        parts.extend(meta)
        parts.append("```")
        parts.append("")

    # 3. 非終端ルール
    parts.append("## 構文ルール\n")
    for name in sorted(nonterminals.keys()):
        parts.append(format_rule_md(name, nonterminals[name]))

    # 4. 終端ルール
    parts.append("## トークン（終端記号）\n")
    for name in sorted(terminals.keys()):
        parts.append(format_terminal_md(name, terminals[name]))

    return "\n".join(parts)


def main():
    lines = load_grammar(GRAMMAR_FILE)
    nonterm, term, meta = split_rules(lines)
    md = build_markdown(nonterm, term, meta)
    OUTPUT_FILE.write_text(md, encoding="utf-8")
    print(f"generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

