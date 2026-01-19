from lark import Lark
from lark.visitors import Interpreter
from sso_objects import HereObject

RESERVED = {"Here", "Moon", "Sun"}

class DummyInterpreter(Interpreter):
    def __init__(self):
        self.env = {}

    def assignment(self, tree):
        name = tree.children[0].value
        if name in RESERVED:
            raise RuntimeError(f"{name} は代入できません")

        value = self.visit(tree.children[1])
        self.env[name] = value
        print(f"{name} = {value}")
        return value

    def constructor(self, tree):
        name = tree.children[0].value
        args = [self.visit(c) for c in tree.children[1:]]

        if name == "Here":
            here = HereObject(*args)
            self.env["Here"] = here
            print("現在地を登録しました")
            return here

        if name == "Moon":
            print("月を評価します（ダミー）")
            return MoonObject(args[0])

        print(f"{name}({args})")
        return None

    def add(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])

        if isinstance(left, HereObject) and isinstance(right, AltObject):
            observer = ObserverObject(left, right.alt)
            return observer

        print("ADD:", left, right)
        return None

    def arrow(self, tree):
        src = self.visit(tree.children[0])
        dst = self.visit(tree.children[1])

        print("観測計算（ダミー）")
        print("仰角: -0.25")
        print("方角: 241.3")
        print("月相: 0.0033")
        return None

    def number(self, tree):
        return float(tree.children[0])

    def NAME_LOWER(self, tok):
        return self.env.get(tok.value, tok.value)

    def NAME_UPPER(self, tok):
        return tok.value
 
    # --------
    # literals / atoms
    # --------

    def var(self, tree):
        name = tree.children[0]
        print(f"[var] {name}")
        return f"<var {name}>"

    def literal(self, tree):
        name = tree.children[0]
        print(f"[literal] {name}")
        return f"<literal {name}>"

    # --------
    # expressions
    # --------

    def sub(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        print(f"[sub] {left} - {right}")
        return f"({left}-{right})"

    def mul(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        print(f"[mul] {left} * {right}")
        return f"({left}*{right})"

    def div(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        print(f"[div] {left} / {right}")
        return f"({left}/{right})"

    def neg(self, tree):
        value = self.visit(tree.children[0])
        print(f"[neg] -{value}")
        return f"(-{value})"

    # --------
    # statements
    # --------

    def statement(self, tree):
        # statement 自体は値を持たない
        for child in tree.children:
            self.visit(child)

