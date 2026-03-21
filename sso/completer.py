"""
補完機能を提供するモジュール。
prompt_toolkitのWordCompleterを使用して、SSOスクリプトのキーワードや天体名を補完します。
"""
from prompt_toolkit.completion import WordCompleter
sso_completer = WordCompleter([
    'Date', 'Direction', 'Observer', 'Now',             # 上位ほど優先順位が高い
    'Time', 'Here', 'Log', 'Echo',
    'Body', 'Home', 'zone',
    'if', 'then', 'else', 'end_if',
    'for', 'in', 'do', 'end_for',
    'while', 'end_while',
    'def', 'end_def',
    ### 天体 ###
    'Sun', 'Mercury', 'Venus',
    'Earth', 'Moon',
    'Mars', 'Phobos', 'Deimos',
    'Jupiter', 'Io', 'Europa', 'Ganymede', 'Callisto',
    'Saturn', 'Mimas', 'Enceladus', 'Tethys', 'Dione', 'Rhea', 'Titan', 'Hyperion', 'Iapetus',
    'Uranus', 'Ariel', 'Umbriel', 'Titania', 'Oberon', 'Miranda',
    'Neptune',
    'Pluto',
    'star',
    ### ephem function ###
    'previous_new_moon', 'next_new_moon',
    'previous_first_quarter_moon', 'next_first_quarter_moon',
    'previous_full_moon', 'next_full_moon',
    'previous_last_quarter_moon', 'next_last_quarter_moon',
    'previous_solstice', 'next_solstice',
    'previous_summer_solstice', 'next_summer_solstice',
    'previous_winter_solstice', 'next_winter_solstice',
    'previous_equinox', 'next_equinox',
    'previous_vernal_equinox', 'next_vernal_equinox',
    'previous_autumnal_equinox', 'next_autumnal_equinox',
    'constellation', 'separation', 'Equatorial', 'Galactic',
    'city', 'delta_t', 'julian_date', 'degrees',
    'to_timezone', 'localtime', 'hour', 'hours'
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

