from prompt_toolkit.completion import WordCompleter
sso_completer = WordCompleter([
    'Date', 'Direction', 'Here', 'Observer', 'Now', 'Time',      # コマンド
    'Sun', 'Mercury', 'Venus',
    'Earth', 'Moon',
    'Mars',
    'Jupiter',
    'Saturn',
    'Uranus',
    'Neptune',
    'Pluto',
    'position', 'velocity', 'azimuth' # プロパティ
], ignore_case=True) # 大文字小文字を区別しない設定

"""
# ネスト型
from prompt_toolkit.completion import NestedCompleter
bodies = {
        'Sun': None, 'Mercury':None, 'Venus':None,
        'Earth':None, 'Moon':None,
        'Mars':None,
        'Jupiter':None,
        'Saturn':None,
        'Uranus':None,
        'Neptune':None,
        'Pluto':None
}

sso_completer = NestedCompleter.from_nested_dict({
    # 命令 -> 天体 -> プロパティ の流れ
    '->': bodies,
    'CALC': bodies,
    # 天体から直接入力する場合（Earth.pos など）
    'Earth': {'.position': None, '.velocity': None},
    'Moon': {'.position': None, '.velocity': None},
    'EXIT': None,
})
"""

