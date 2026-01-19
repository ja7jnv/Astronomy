from lark import Lark
from lark.exceptions import UnexpectedToken
from interpreter import DummyInterpreter

GRAMMAR_FILE = "sso.lark"

def main():
    with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
        grammar = f.read()

    parser = Lark(
        grammar,
        parser="lalr",
        start="start",
        propagate_positions=True,
        maybe_placeholders=False,
    )

    print("Lark interactive parser")
    print("Ctrl-D or Ctrl-C to exit")
    print("-" * 60)

    buffer = ""
    continuing = False

    while True:
        try:
            prompt = "... " if continuing else ">>> "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        stripped = line.rstrip()

        if stripped.endswith("\\"):
            # 継続行：改行を入れない
            buffer += stripped[:-1] + " "
            continuing = True
            continue
        else:
            # 最終行
            if continuing:
                buffer += stripped.lstrip() + "\n"
            else:
                buffer += line + "\n"
            continuing = False

        try:
            tree = parser.parse(buffer)
            # print(tree.pretty())

            interp = DummyInterpreter()
            interp.visit(tree)

        except UnexpectedToken as e:
            print("\n[Parse error]")
            print(e)

        buffer = ""

if __name__ == "__main__":
    main()

