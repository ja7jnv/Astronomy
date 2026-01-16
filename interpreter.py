from lark.visitors import Interpreter


class DummyInterpreter(Interpreter):
    # --------
    # literals / atoms
    # --------

    def number(self, tree):
        value = tree.children[0]
        print(f"[number] {value}")
        return float(value)

    def var(self, tree):
        name = tree.children[0]
        print(f"[var] {name}")
        return f"<var {name}>"

    def literal(self, tree):
        name = tree.children[0]
        print(f"[literal] {name}")
        return f"<literal {name}>"

    def constructor(self, tree):
        name = tree.children[0]
        args = [self.visit(child) for child in tree.children[1:]]
        print(f"[constructor] {name}({args})")
        return f"<{name} {args}>"

    # --------
    # expressions
    # --------

    def add(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        print(f"[add] {left} + {right}")
        return f"({left}+{right})"

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

    def arrow(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        print(f"[arrow] {left} -> {right}")
        print(type(left), type(right))
        return f"({left} -> {right})"

    # --------
    # statements
    # --------

    def assignment(self, tree):
        name = tree.children[0]
        value = self.visit(tree.children[1])
        print(f"[assign] {name} = {value}")
        return (name, value)

    def statement(self, tree):
        # statement 自体は値を持たない
        for child in tree.children:
            self.visit(child)

