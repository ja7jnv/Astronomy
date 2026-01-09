import ephem
import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
from math import degrees as deg

# JST (日本標準時) のタイムゾーンオブジェクトを作成
JST = ZoneInfo("Asia/Tokyo")

# .envファイルをロード（同階層にある.envを探して読み込む）
load_dotenv()

# Body(天体)クラスのインスタンスを作成。
moon = ephem.Moon()

# Observer(観測者)クラスのインスタンスを作成。
# 取得したい場所の緯度と経度を指定
LATITUDE  = os.getenv("OBSERVATION_LATITUDE")
LONGITUDE = os.getenv("OBSERVATION_LONGITUDE")
ELEVATION = os.getenv("OBSERVATION_ELEVATION")
if not (LATITUDE and  LONGITUDE and ELEVATION):
    print("エラー: 位置情報が見つかりません。.envファイルを確認してください>。")
    exit()

obs = ephem.Observer()
obs.lat = LATITUDE
obs.lon = LONGITUDE
obs.elevation = float(ELEVATION)
obs.date = datetime.datetime.now(datetime.UTC)

# 観測者から見た天体を計算。

moon.compute(obs)
print(f"日時：{datetime.datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S %Z')}")
print(f"地平線からの仰角：{deg(moon.alt)}")
print(f"方角：{deg(moon.az)}")
print(f"月相：{moon.moon_phase}  輝面比（光っている部分の割合）")
print(f"月齢：{obs.date - ephem.previous_new_moon(obs.date)}")

