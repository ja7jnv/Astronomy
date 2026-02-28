mag_guide = [
        "[bold bright_white]夜空で非常に明るく輝く[/bold bright_white]", # -等星
        "[bright_white]夜空で明るく輝く[/bright_white]",                 # 0等星
        "[bright_white]夜の街なかでも明るい[/bright_white]",             # 1
        "[white]夜の街なかでなんとか見える[/white]",                     # 2
        "[gray62]夜でも街では見えづらい[/gray62]",
        "[gray50]郊外の暗い空で見えるレベル[/gray50]",
        "[gray42]郊外の暗い空でも見えづらい[/gray42]",
        "[gray30]肉眼で見える限界の明るさ[/gray30]",
        "[gray19]双眼鏡(7× 50：9.5 等まで) や望遠鏡が必要[/gray19]"     # 7
]

planet = {
        "Mercury"   :   "水星",
        "Venus"     :   "金星",
        "Earth"     :   "地球",
        "Mars"      :   "火星",
        "Jupiter"   :   "木星",
        "Saturn"    :   "土星",
        "Uranus"    :   "天王星",
        "Neptune"   :   "海王星",
        "Pluto"     :   "冥王星"
}


help_help = [
        "\n" + "="*30,
        "【コマンド入力形式のガイド】",
        "  代入 : 変数 = コマンド名(引数)",
        "  観測 : 観測地 -> 天体名",
        "  月食 : Sun -> 観測地 -> Moon",
        "",
        "観測時刻を指定するには変数Timeに日付時刻を代入します。",
        "方法は help Time で確認してください。",
        "Timeには、あらかじめSSO起動時の時刻が入ってます。",
        "観測地の設定はObserverコマンドで行います。",
        "方法は help Observer で確認してください。",
        "観測地にHereを指定すると構成情報 config.ini で設定した現在地が使われます。",
        "",
        "天体名は、先頭文字が大文字の星の名前です。 例：Sun Moon",
        "help Body で指定可能な天体名が表示されます。",
        "コマンド名や天体名はTabキーで文字入力補完機能が使えます。",

        "- 終了するには 'exit' または 'quit' と入力してください。",
        "="*30 + "\n",
        "コマンド一覧(主要なもの):",
        " Date  Now  Observer  Direction  Print  Mountain"
]


command_help = {
    "_body_common_":    "天体名として指定可能な名称: ＊現在Moon以外の衛星は未サポートです＊",
    "Moon":     "月のhelp",
    "Time":     "観測時刻を決めるシステム変数\n" \
                "設定例: sso> Time = Date('2026/4/10 20:00:00')   ＊必ず秒まで入力\n" \
                "      : sso> Time = Date()   ＊引数を省略すると対話的に日付時刻入力ができる",
    "Date":     "日付時刻を設定するコマンド"
}

