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
        try:
            line = input(">>> ")
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        buffer += line + "\n"

        # セミコロンが来たら 1 単位としてパース
        if ";" not in buffer:
            continue

        try:
            tree = parser.parse(buffer)
            print("\n[Parse tree]")
            print(tree.pretty())
        except Exception as e:
            print("\n[Parse error]")
            print(e)

        buffer = ""


if __name__ == "__main__":
    main()

