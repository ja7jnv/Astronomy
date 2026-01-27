"""
このモジュール内のクラスは、すべてUTCで処理する。
JTSや他の地方時は、その変換メソッド以外では一切考慮しない。
"""
import ephem
import math
from datetime import datetime

import logging # ログの設定
logging.basicConfig(
level=logging.DEBUG, # 出力レベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger =  logging.getLogger(__name__)

# システム設定管理クラス（シングルトン的な役割）
class SSOSystemConfig:
    def __init__(self):
        self.env = {"Tz" : 9.0,
                    "Echo" : True,
                    "Here" : ephem.Observer(),
                    "Time" : ephem.now()
        }

    def set_Tz(self, value):
        self.env["Tz"] = float(value)
        return f"UTCからの時差: +{self.env["Tz"]:g}"

    def set_Echo(self, value):
        # 0, Off, False などをオフとみなす柔軟な処理
        s_val = str(value).lower()
        self.env["Echo"] = s_val not in ["0", "off", "false"]
        return f"Echo mode: {'On' if self.env["Echo"] else 'Off'}"

    def set_Here(self, value):
        self.env["Here"] = value
        return f"Default ovserver: {self.env["Here"]}"

    def set_Time(self, value):
        self.env["Time"] = value
        return f"Observation date_time: {self.env["Time"]}"

    def SSOEphem(self, attr, value=None):
        logger.debug(f"ephem call: ephem.{attr}({value})")
        # もし値が渡されなければ、現在の設定(self.env)から取得する
        if value is None:
            if attr == "Date":
                value = self.env["Time"]
            elif attr == "Observer":
                value = self.env["Here"]

        # valueがNoneなら []、あれば [value]
        args = [value] if value is not None else []

        # 1. ephemオブジェクトを取得
        target = getattr(ephem, attr)(*args)

        # 2. もし計算が必要なオブジェクト（天体など）なら、
        #    現在の設定(self.env)にある観測地や時刻を自動適用する
        if hasattr(target, 'compute'):
            target.compute(self.env["Here"]) # ここで self.env を活用！

        return target


class SSOObserver:
    def __init__(self, attr, lat=None, lon=None, elev=0, config=None):
        self.attr = attr
        self.lat, self.lon, self.elev = lat, lon, elev
        self.ephem_obs = ephem.Observer()
        if lat is not None:
            self.ephem_obs.lat, self.ephem_obs.lon = str(lat), str(lon)
            self.ephem_obs.elevation = elev
            # 初期状態は現在時刻(UTC)
            self.ephem_obs.date = config.env["Time"]

    def __repr__(self):
        return f"({self.attr})\n Lat: {self.lat}\n Lon: {self.lon}\n Elev: {self.elev}"

class SSOCalculator:
    @staticmethod
    def observe(observer, target_name, config, mode="Now", context=None):
        """
        config: 時差表示のために必要
        """
        obs = observer.ephem_obs
        
        # 天体取得 (Moon固定ではなく、ephemにあるものを動的に取得)
        try:
            body = getattr(ephem, target_name)()
        except AttributeError:
            return f"Error: Unknown body '{target_name}'"

        body.compute(obs)
        
        def to_deg(rad): return math.degrees(rad)
        
        # 結果表示用のTimeオブジェクト作成ヘルパー
        def make_time(edate): return SSOTime(None, config=config) # 中身を入れ替える
        
        # 実際には SSOTime(edate, config) のように初期化したいが
        # SSOTimeの実装に合わせて日付をセットする
        def format_time(edate):
            t = SSOTime(None, config=config)
            t.date = edate
            return t

        if mode == "Now":
            return (f"{observer.name}:\n 時刻: {format_time(obs.date)}\n"
                    f" 方角: {to_deg(body.az):.2f}°\n 高度: {to_deg(body.alt):.2f}°\n"
                    f" 月齢: {getattr(body, 'phase', '-')}")
        
        if mode in ["Rise", "Set"]:
            try:
                method = obs.next_rising if mode == "Rise" else obs.next_setting
                event_time = method(body)
                return f"{observer.name}:\n {target_name}の{'出' if mode=='Rise' else '没'}: {format_time(event_time)}"
            except ephem.AlwaysUpError:
                return f"{target_name} は沈みません"
            except ephem.NeverUpError:
                return f"{target_name} は昇りません"
        
        return "Unknown Mode"
