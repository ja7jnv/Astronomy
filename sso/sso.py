# sso.py
import sys
from lark import Lark
from interpreter import SSOInterpreter
from classes import SSOBase

# 文法ファイルの読み込み
with open("sso.lark", "r", encoding="utf-8") as f:
    grammar = f.read()

parser = Lark(grammar, parser='lalr', start='start')
interpreter = SSOInterpreter()

def repl():
    print("Solar System Observer DSL (type 'exit' to quit)")
    print(">>> Tz = 9 // Default Timezone") # 
    
    while True:
        try:
            text = input(">>> ") # 
            if text.strip() in ["exit", "quit"]:
                break
            if not text.strip():
                continue

            # ヒストリー機能は input() が標準でサポートする環境が多いが、
            # 明示的には readline モジュールを import することで有効化される（Unix系）
            
            tree = parser.parse(text + "\n") # 末尾に改行を付与して解析
            
            # 各ステートメントを実行
            for statement in tree.children:
                if statement.data == 'statement':
                    # statement -> (assign | expr)
                    child = statement.children[0]
                    result = interpreter.transform(child)
                    
                    # Echo制御 [cite: 2, 3]
                    if interpreter.echo and result is not None:
                        # 代入文の場合は結果を表示しない等の制御も可能だが、
                        # プロンプト例では代入後もエコーしている
                        print(f"{result}")

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    repl()
