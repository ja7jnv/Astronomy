from lark import Lark
from lark.visitors import Interpreter
from sso_objects import *

RESERVED = {"Here", "Moon", "Sun"}

class SSOInterpreter(Interpreter):
    def __init__(self):
        self.env = {}

    # -------- statements --------

    def assignment(self, tree):
        name = tree.children[0].value
        if name in RESERVED:
            raise RuntimeError(f"{name} は代入できません")

        value = self.visit(tree.children[1])
        self.env[name] = value
        print(f"{name} = {value}")
        return value

    def expr_statement(self, tree):
        value = self.visit(tree.children[0])
        if isinstance(value, HereObject):
            value.show()
        elif value is not None:
            print(value)
        return value

    # -------- expressions --------

    def arrow(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        print(f"ARROW: {left} -> {right}")
        return ("arror", left, right)

    def add(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        print("ADD:", left, "+", right)
        return None

    # -------- atoms --------

    def constructor(self, tree):
        name = tree.children[0].value
        args = [self.visit(c) for c in tree.children[1:]]

        if name == "Here":
            here = self._build_here(args)
            self.env["Here"] = here
            return here

        print(f"{name}({args})")
        return None

    def kwarg(self, tree):
        name = tree.children[0].value
        value = self.visit(tree.children[1])
        return KwArg(name, value)

    def var(self, tree):
        name = tree.children[0].value
        return self.env.get(name, name)

    def number(self, tree):
        return float(tree.children[0])

    # -------- helpers --------

    def _build_here(self, args):
        lat = lon = elev = None
        pos = []

        for a in args:
            if isinstance(a, KwArg):
                if a.name == "Lat":
                    lat = a.value
                elif a.name == "Lon":
                    lon = a.value
                elif a.name == "Elev":
                    elev = a.value
                else:
                    print(f"Unknown keyword: {a.name}")
            else:
                pos.append(a)

        if pos:
            if lat is None and len(pos) > 0:
                lat = pos[0]
            if lon is None and len(pos) > 1:
                lon = pos[1]
            if elev is None and len(pos) > 2:
                elev = pos[2]

        return HereObject(lat, lon, elev)
