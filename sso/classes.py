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

def boolean_setter(key_name):
    """
    1/0, on/off, true/false, yes/no を Yes/No に変換するデコレータ
    """
    def decorator(func):
        def wrapper(self, value):
            # 前処理：共通の変換ロジック
            s_val = str(value).lower()
            if s_val in ["0", "off", "false", "no"]:
                final_val = "No"
            elif s_val in ["1", "on", "true", "yes"]:
                final_val = "Yes"
            else:
                # 不明な値が来た場合の処理（必要に応じて）
                final_val = value

            # 辞書の更新
            self.env[key_name] = final_val

            # 元の関数（リターンメッセージの生成など）を実行
            return f"{key_name} mode: {self.env.get(key_name)}"
        return wrapper
    return decorator

##
# システム設定管理クラス（シングルトン的な役割）
#
class SSOSystemConfig:
    def __init__(self):
        self.env = {"Tz" : 9.0,
                    "Echo" : "Yes",
                    "Log"  : "No",
                    "Here" : ephem.Observer(),
                    "Time" : ephem.now()
        }

    def set_Tz(self, value):
        self.env["Tz"] = float(value)
        return f"UTCからの時差: +{self.env["Tz"]:g}"

    @boolean_setter("Echo")
    def set_Echo(self, value):
        pass

    @boolean_setter("Log")
    def set_Log(self, value):
        pass

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

    def fromUTC(self, utc_val):
        tz_offset = self.env['Tz']

        # 引数が既に datetime オブジェクトならそのまま使う
        if isinstance(utc_val, datetime):
            dt_utc = utc_val
        else:
            # 文字列の場合は、ハイフン区切り等にも対応できるよう変換
            dt_utc = datetime.strptime(str(utc_val), "%Y/%m/%d %H:%M:%S")

        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        tz = timezone(timedelta(hours=tz_offset))
        dt_local = dt_utc.astimezone(tz)
        date_part = dt_local.strftime("%Y/%m/%d")
        time_part = dt_local.strftime("%H:%M:%S")

        sign = "+" if tz_offset >= 0 else ""
        offset_str = f"[{sign}{tz_offset}]"

        return f"{date_part:<10} {time_part:<8} {offset_str}"

    def reformat(self, body, target=None, config=None):
        logger.debug(f"reformat:\nbody:{body}\ntarget:{target}")
        match body:
            case ephem.Observer():
                match target:
                    case ephem.Moon():
                        value = self.reformat_moon(body, target, config)
                    case None:
                        value = self.reformat_observer(body)
                    case _:
                        value = self.reformat_planet(body, target)

            case ephem.Moon():
                value = self.reformat_moon(config.env["Here"], body, config)

            case    _:
                value = None
                
        return value

    def reformat_observer(self, body):
        value = f"\n観測日時：{self.fromUTC(body.date)}"
        value = value + f"\n緯度：{body.lat}"
        value = value + f"\n経度：{body.lon}"
        value = value + f"\n標高：{body.elevation}"
        return value

    def reformat_moon(self, obs, moon, config):
        logging.debug(f"reformat_moon:\nobs:{obs}\nmoon:{moon}")
        value = ""

        # 観測日
        obs_time = obs.date
        local_obs_time = self.fromUTC(obs_time)
        value = value + f"観測日時：{local_obs_time}\n"

        value = value + "\n"

        # 観測時刻の月の位置計算
        moon.compute(obs)
        value = value + f"月の高度・方位\n"
        value = value + f"輝面比: {moon.phase:.2f}%\n"
        value = value + f"月齢  : {obs.date - ephem.previous_new_moon(obs.date):.2f}\n"

        # 月の高度と方位
        alt = math.degrees(moon.alt)
        az  = math.degrees(moon.az)
        value = value + f"高度  ：{alt:.2f}°  方位：{az:.2f}°\n"

        diameter = math.degrees(moon.size) * 60.0
        value = value + f"視直径：{diameter} arcmin\n"

        distance = moon.earth_distance
        value = value + f"距離　：{distance} AU\n"
        value = value + "\n"
        # -----------------------------------------------

        # 月の出／入時刻、南中時刻の計算
        # 方針：観測日（現地時間）の「00:00:00」を計算開始地点にする

        # 1. 現在の観測日時を一度ローカルタイム(datetime型)にする
        utc_now = obs_time.datetime().replace(tzinfo=timezone.utc)

        # JSTなどローカルのタイムゾーン情報を環境変数から取得
        tz_offset = timezone(timedelta(hours=float(config.env["Tz"]))) # 日本の場合

        local_now = utc_now.astimezone(tz_offset)

        # 2. その日の「00:00:00」を作成 (現地時間)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 3. 計算開始用にUTCに戻す
        start_utc = local_midnight.astimezone(timezone.utc)

        # 4. PyEphemの計算時間をセット
        obs.date = ephem.Date(start_utc)

        moon.compute(obs)

        # --- 次の月の出・南中・月の入を計算 ---
        try:
            rise_time = obs.next_rising(moon)
            local_rise_dt = rise_time.datetime().astimezone(tz_offset)
            # 日付が変わっていないかチェック（「今日」の月の出か？）
            if local_rise_dt.date() != local_midnight.date():
                 rise_str = "--:-- (なし)"
                 rise_az_str = "---"
            else:
                 rise_str = self.fromUTC(rise_time.datetime())
                 # 方位計算
                 obs_temp = ephem.Observer()
                 obs.date = rise_time
                 moon.compute(obs)
                 rise_az_str = f"{math.degrees(moon.az):6.2f}"
        except ephem.AlwaysUpError:
             rise_str = "一日中地平線上"
             rise_az_str = "---"
        except ephem.NeverUpError:
             rise_str = "一日中地平線下"
             rise_az_str = "---"

        try:
            zenith = obs.next_transit(moon)
            local_zenith_dt = zenith.datetime().astimezone(tz_offset)
            if local_zenith_dt.date() != local_midnight.date():
                zenith_str = "--:-- (なし)"
                zenith_alt_str = "---"
            else:
                zenith_str = self.fromUTC(zenith.datetime())
                # 高度計算
                obs.date = zenith
                moon.compute(obs)
                zenith_alt_str = f"{math.degrees(moon.alt):6.2f}"
        except:
             zenith_str = "---"
             zenith_alt_str = "---"

        try:
            set_time = obs.next_setting(moon)
            local_set_dt = set_time.datetime().astimezone(tz_offset)
            if local_set_dt.date() != local_midnight.date():
                set_str = "--:-- (なし)" # 明日のセットになる場合
            else:
                set_str = self.fromUTC(set_time.datetime())

            # 月の入の方位計算
            obs.date = set_time
            moon.compute(obs)
            set_az_str = f"{math.degrees(moon.az):6.2f}"

        except:
             set_str = "---"
             set_az_str = "---"

        sun = ephem.Sun()
        transit_time = obs.next_transit(sun)
        utc_noon = transit_time.datetime().replace(tzinfo=timezone.utc)
        age = obs.date - ephem.previous_new_moon(utc_noon)

        value = value + f"月の出入り：\n"
        value = value + f"月の出：{rise_str:<26}  方位：{rise_az_str}°\n"
        value = value + f"南中  ：{zenith_str:<26}  高度：{zenith_alt_str}°\n"
        value = value + f"月の入：{set_str:<26}  方位：{set_az_str}°\n"
        value = value + f"月齢  ：{age:.1f}\n"

        # 最後に念のためobs.dateを元に戻しておく
        obs.date = obs_time

        return value


    def reformat_planet(self, obs, planet):
        value = f"惑星の処理コードは未実装"
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
 
    @classmethod
    def observe(observer, target_name, config, mode="Now", context=None):
        
        # 天体取得 (Moon固定ではなく、ephemにあるものを動的に取得)
        try:
            body = getattr(ephem, target_name)()

        except AttributeError:
            return f"Error: Unknown body '{target_name}'"

        body.compute(observer)
        
        def to_deg(rad):
            return math.degrees(rad)
        
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
