from lark import Lark, Tree
import sys

GRAMMAR_FILE = "example.lark"

def main():
    # Lark 文法の読み込み
    with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
        grammar = f.read()

    parser = Lark(
        grammar,
        parser="lalr",
        start="program",
        propagate_positions=True,
        maybe_placeholders=False,
    )

    print("Lark interactive parser")
    print("Input code terminated by ';' (Ctrl-D or Ctrl-C to exit)")
    print("-" * 60)

    buffer = ""

    while True:
        line = input(">>> ")
        buffer += line + "\n"

        try:
            tree = parser.parse(buffer)
            print(tree.pretty())
            buffer = ""

        except Exception:
            continue


if __name__ == "__main__":
    main()

