"""
このモジュール内のクラスは、すべてUTCで処理する。
JTSや他の地方時は、その変換メソッド以外では一切考慮しない。
"""
import ephem
import math
from datetime import datetime, timezone, timedelta

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

    def SSOEphem(self, attr, value=None, config=None):
        logger.debug(f"ephem call: ephem.{attr}({value})")
        # もし値が渡されなければ、現在の設定(self.env)から取得する
        if value is None:
            if attr == "Date":
                value = self.env["Time"]
            elif attr == "Observer":
                value = self.env["Here"]

        # valueがNoneなら []、あれば [value]
        args = [value] if value is not None else []

        target = getattr(ephem, attr)(*args)
        logger.debug(f"ephem.{attr}({args}) -> {target}")

        # もし計算が必要なオブジェクト（天体など）なら、
        # 現在の設定(self.env)にある観測地や時刻を自動適用する。
        # しかし、挙動がおかしいので、一旦無効。
        #if hasattr(target, 'compute'):
        #    logger.debug(f"target:{target}.compute({self.env['Here']}")
        #    target.compute(self.env["Here"])

        return target

    def toUTC(self, tz_date):
        d_str = tz_date + "+" + f"{int(self.env['Tz']*100):04}"
        dt =  datetime.strptime(d_str, "%Y/%m/%d %H:%M:%S%z")
        return dt.astimezone(timezone.utc)

    def fromUTC(self, utc_str):
        tz_offset = self.env['Tz']
        dt_utc = datetime.strptime(str(utc_str), "%Y/%m/%d %H:%M:%S")
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        tz = timezone(timedelta(hours=tz_offset))
        dt_local = dt_utc.astimezone(tz)
        date_part = dt_local.strftime("%Y/%-m/%-d")
        time_part = dt_local.strftime("%-H:%M:%S")

        sign = "+" if tz_offset >= 0 else ""
        offset_str = f"({sign}{tz_offset})"

        return f"{date_part} {time_part} {offset_str}"

    def reformat(self, body):
        logger.debug(f"reformat: {body}")
        if isinstance(body, ephem.Observer):
            value = f"\n 観測日時：{self.fromUTC(body.date)}"
            value = value + f"\n 緯度：{body.lat}"
            value = value + f"\n 経度：{body.lon}"
            value = value + f"\n 標高：{body.elevation}"
        elif isinstance(body, ephem.Moon):
            value = f"\n 黄道座標系における位置"
            value = value + f"\n 日心緯度：{body.hlat}"
            value = value + f"\n 日心経度：{body.hlon}"

        return value


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
