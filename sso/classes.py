"""
このモジュール内のクラスは、すべてUTCで処理する。
JTSや他の地方時は、その変換メソッド以外では一切考慮しない。

"""
import ephem
import math
import numpy as np
from datetime import datetime, timezone, timedelta, time
from typing import Optional, Tuple, Dict, Any
from abc import ABC, abstractmethod

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# rich.console の集約
from rich.console import Console
#console = Console(height=100)
console = Console()

from pygments.lexer import RegexLexer
from pygments.token import Keyword, Name, String, Number, Operator, Punctuation, Comment, Text

class SSOLexer(RegexLexer):
    name = 'sso'

    tokens = {
        'root': [
            # コメント (Lark: COMMENT)
            (r'//.*', Comment.Single),
            # 数値 (Lark: SIGNED_NUMBER)
            (r'-?\d+\.?\d*([eE][+-]?\d+)?', Number),
            # 文字列 (Lark: STRING)
            (r'"[^"]*"|\'[^\']*\'', String),
            # 演算子 (Lark: ->, +, -, *, /, ^, =)
            (r'->|\+|-|\*|/|\^|=', Operator),
            # 区切り文字
            (r'[();,.]', Punctuation),
            # BODY_NAME (大文字開始: クラスや天体イメージ)
            (r'[A-Z][a-zA-Z0-9_]*', Name.Class),
            # VAR_NAME (小文字開始: 変数イメージ)
            (r'[a-z][a-zA-Z0-9_]*', Name.Variable),
            # 空白
            (r'\s+', Text),
        ]
    }


# ===== 定数定義 =====
class Constants:
    """定数クラス"""
    DEFAULT_TIMEZONE = 9.0
    DEFAULT_ECHO = "No"
    DEFAULT_LOG = "No"
    
    MODE_NOW = "Now"
    MODE_RISE = "Rise"
    MODE_SET = "Set"
    MODE_ZENITH = "Zenith"
    
    EVENT_ALWAYS_UP = "AlwaysUp"
    EVENT_NEVER_UP = "NeverUp"

    """天文定数(SI単位系)"""
    ATMOSPHERIC_PRESSURE = 1013.25  # 標準大気圧 1013.25 (hPa)
    AVERAGE_TEMPERATURE = 15.0   # 計算に使う平均気温 (15℃)
    EARTH_RADIUS = 6378137.0     # 地球半径(m)
    AXIAL_TILT_DEG = 23.439      # 地軸傾斜角(度)
    JULIAN_DAY_J2000 = 2451545.0 # J2000.0のユリウス日
    KM_PER_DEGREE_LAT = 111320   # 緯度1度あたりのm
    INTERCARDINAL =  8           # 方位分割 4, 8, 16
    MOONSET_ALTITUDE = -1.2      # 月没判断高度 -1.2度
    LUNAR_CYCLE = 29.53          # 月の周期
    ANGLE_LUNAR_ECLIPSE = 0.0262 # 約1.5度 (ラジアン)
    LUNAR_ECLIPSE_PARTIAL = 0.018 # 半影食の限界値 0.015近辺で調整
    LUNAR_ECLIPSE_SF = 1.02      # 計算誤差許容値
    LUNAR_ECLIPSE_SCALE_FACTOR = 51 / 50    # ↑と同じ？

    """予約語"""
    KEYWORD = ( "Sun",
                "Mercury",
                "Venus",
                "Earth", "Moon",
                "Mars",
                "Jupiter", "Io", "Europa", "Ganymede", "Callisto",
                "Saturn",
                "Uranus",
                "Neptune",
                "Pluto"
    )

    """エラーメッセージ"""
    ERR_HERE = "環境変数Hereへの代入はObserverコマンドの返り値を指定してください。"
    ERR_TZ = "時差の設定は-12から14の範囲で指定してください。"
    ERR_TIME = "観測時刻の設定はephem.Dateの形式で指定してください。"


def boolean_setter(key_name: str):
    """
    1/0, on/off, true/false, yes/no を Yes/No に変換するデコレータ
    """
    def decorator(func):
        def wrapper(self, value):
            s_val = str(value).lower()
            if s_val in ["0", "off", "false", "no"]:
                final_val = "No"
            elif s_val in ["1", "on", "true", "yes"]:
                final_val = "Yes"
            else:
                final_val = value
            
            self.env[key_name] = final_val
            return f"{key_name} mode: {self.env.get(key_name)}"
        return wrapper
    return decorator


# ===== システム設定管理クラス =====
class SSOSystemConfig:
    """システム設定管理クラス（リファクタリング版）"""
    
    def __init__(self):
        self.env = {
            "Tz"    : Constants.DEFAULT_TIMEZONE,
            "Echo"  : Constants.DEFAULT_ECHO,
            "Log"   : Constants.DEFAULT_LOG,
            "Time"  : ephem.now(),
            "Direction" : int(8),
            "Earth" : ephem.Observer(),
            "Here"  : ephem.Observer(),
            "Chokai": ephem.Observer()
        }

        # Ephemが標準でサポートしている太陽系の天体リスト（name: ３番目の要素）
        self.body = [name for _0, _1, name in ephem._libastro.builtin_planets()]
        #                     ^^^^^^ １番目と２番めの要素は無視

    @boolean_setter("Echo")
    def set_Echo(self, value):
        """エコーモードを設定"""
        pass
    
    @boolean_setter("Log")
    def set_Log(self, value):
        """ログモードを設定"""
        pass
    
    def set_Tz(self, value: float) -> str:
        """タイムゾーンを設定"""
        if -12.0 <= value <= 14.0:
            self.env["Tz"] = float(value)
            return f"UTCからの時差: {self.env['Tz']:+.2f}"
        raise AttributeError(Constants.ERR_TZ)
    
    def set_Here(self, value: ephem.Observer) -> str:
        """デフォルト観測地を設定"""
        if not isinstance(value, ephem.Observer):
            raise AttributeError(Constants.ERR_HERE)
        self.env["Here"] = value
        return f"Default observer: {self.env['Here']}"
    
    def set_Time(self, value) -> str:
        """観測時刻を設定"""
        if not isinstance(value, ephem.Date):
            raise AttributeError(Constants.ERR_TIME)
        self.env["Time"] = value
        return f"Observation date_time: {self.env['Time']}"
    
    def SSOEphem(self, attr: str, value=None):
        """ephemの関数やクラスを呼び出す"""
        logger.debug(f"SSOEphem: ephem.{attr}({value})")
        
        args = [value] if value is not None else []
        target = getattr(ephem, attr)(*args)
        logger.debug(f"SSOEphem: ephem.{attr}({args}) -> {target}")
        
        return target
    
    def toUTC(self, tz_date: str) -> datetime:
        """ローカル時刻をUTCに変換"""
        d_str = tz_date + "+" + f"{int(self.env['Tz']*100):04}"
        dt = datetime.strptime(d_str, "%Y/%m/%d %H:%M:%S%z")
        return dt.astimezone(timezone.utc)
    
    def fromUTC(self, utc_val) -> str:
        """UTCをローカル時刻に変換してフォーマット"""
        tz_offset = self.env['Tz']
        
        if isinstance(utc_val, datetime):
            dt_utc = utc_val
        else:
            dt_utc = datetime.strptime(str(utc_val), "%Y/%m/%d %H:%M:%S")
        
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        tz = timezone(timedelta(hours=tz_offset))
        dt_local = dt_utc.astimezone(tz)
        
        date_part = dt_local.strftime("%Y/%m/%d")
        time_part = dt_local.strftime("%H:%M:%S")
        
        sign = "+" if tz_offset >= 0 else ""
        offset_str = f"[{sign}{tz_offset}]"
        
        return f"{date_part:<10} {time_part:<8} {offset_str}"


class SSOObserver:
    """観測地オブジェクト"""
    
    def __init__(
        self, 
        attr: str, 
        lat: Optional[float] = None, 
        lon: Optional[float] = None, 
        elev: float = 0, 
        config: Optional[SSOSystemConfig] = None
    ):
        self.attr = attr
        self.lat, self.lon, self.elev = lat, lon, elev
        self.ephem_obs = ephem.Observer()
        
        if lat is not None:
            self.ephem_obs.lat, self.ephem_obs.lon = str(lat), str(lon)
            self.ephem_obs.elevation = elev
            
            """
            if config:
                self.ephem_obs.date = config.env["Time"]
            """
    
    def __repr__(self) -> str:
        return f"({self.attr})\n Lat: {self.lat}\n Lon: {self.lon}\n Elev: {self.elev}"

class SSOEarth:
    def __init__(self, earth: ephem.Observer):
        logger.debug(f"SSOEarth: earth={earth}")
        self.sun  = ephem.Sun(earth)
        self.obs  = earth
        self.moon = ephem.Moon(earth)
        self.mode = None

        self.obs.pressure = Constants.ATMOSPHERIC_PRESSURE
        self.obs.temp = Constants.AVERAGE_TEMPERATURE

#大阪市立科学館のWEBを参考に書き換える
# http://www.sci-museum.kita.osaka.jp/~egoshi/astronomy/python/python_lunar_eclipse.html#:~:text=for%20x%20in%20range(0,(max_eclipse%5B1%5D))

    def lunar_eclipse(self, period: int, place:str) -> Any:
        logger.debug(f"lunar_eclipse: date: {period}, obs={self.obs}, moon={self.moon}, sun={self.sun}")
        config      = SSOSystemConfig()
        date        = []
        separation  = []
        altitude    = []
        status      = []
        max_time    = []
        magnitude   = []
        begin_time  = []
        end_time    = []

        def set_return_status():
            stat = "皆既/部分食" if s < Constants.LUNAR_ECLIPSE_PARTIAL else "半影月食"
            status.append(stat)
            date.append(full_moon.datetime())
            separation.append(s)
            altitude.append(moon.alt)
            max_time.append(res[0])
            magnitude.append(res[1])
            begin_time.append(res[2])
            end_time.append(res[3])
            logger.debug(f"lunar_eclipse: date={full_moon}, sep={s}, status-{status}")
        ### set_return_status():
        ### end of def

        obs = ephem.Observer()              # 月食日を求めるためのObserver
        obs.date = self.obs.date            # 観測地Observerのdateを代入
        obs.elevation = -Constants.EARTH_RADIUS  # -6378137.0 地球中心
        obs.pressure = 0
        obs.temp =  0

        is_world = (place == "world")       # 全地球での観測か？

        # 満月（月食候補）を調べる
        for i in range(period*12): # 調査年数periodに年間発生満月回数12を乗じる
            full_moon = ephem.next_full_moon(obs.date)
            obs.date = full_moon            # 月食日探索用Observerの日付更新
            self.obs.date = full_moon       # 観測地Observerの日付更新

            sun = ephem.Sun(obs)
            moon = ephem.Moon(obs)
            moon_here = ephem.Moon(self.obs)

            # 太陽と月の離角を計算（ラジアン）
            # 月食は離角が180度（πラジアン）に近い時に起こる
            sep = ephem.separation(moon, sun)
            s = abs(sep - math.pi)

            # TODO - この条件、要検討　2027/02/21 半影月食のケース
            is_moon_up = (moon_here.alt > math.radians(Constants.MOONSET_ALTITUDE))
            # 地球の影（本影＋半影）のサイズからして、
            # 約0.025ラジアン以内なら何らかの食が起きる
            scale_factor = Constants.LUNAR_ECLIPSE_SCALE_FACTOR   # 誤差許容値1.02
            if s < Constants.ANGLE_LUNAR_ECLIPSE * scale_factor:
                # その地点で月が観測地点の地平線より上にあるか
                if is_world or is_moon_up:
                    res = self.get_eclipse_time(obs.date)
                    set_return_status()

        return {"date": date,
                "separation": separation,
                "altitude": altitude,
                "status": status,
                "max_time": max_time,
                "magnitude": magnitude,
                "begin_time": begin_time,
                "end_time": end_time
                }


    # TODO 時間探索を観測地で実施する必要あり
    def get_eclipse_time(self, initial_date: datetime) -> dict:
        from operator import itemgetter

        obs = ephem.Observer()
        obs.elevation = -Constants.EARTH_RADIUS 
        obs.pressure = 0
        start_date = ephem.Date(initial_date - (2 * ephem.hour)) # 満月時刻から２時間前

        sun = ephem.Sun()
        moon = ephem.Moon()

        res = []            # [時刻, 食分] のリスト
        eclipse = []        # begin:, max:, end:, magnitude: の辞書型

        # 1秒ずつ4時間分　計算繰り返し
        for x in range(0, 15000):
            # 時刻を1秒進める
            obs.date = start_date.datetime() + timedelta(seconds = x)

            # 太陽・月の位置・半径計算
            sun.compute(obs)
            moon.compute(obs)
            r_s = sun.size/2
            r_m = moon.size/2

            # 視差・本影の視半径計算
            p_s = np.rad2deg(ephem.earth_radius / (sun.earth_distance * ephem.meters_per_au)) * 3600    # 度-> 秒
            p_m = np.rad2deg(ephem.earth_radius / (moon.earth_distance * ephem.meters_per_au)) * 3600
            R_u = (p_s + p_m - r_s) * Constants.LUNAR_ECLIPSE_SCALE_FACTOR
            R_p = (p_s + p_m + r_s) * Constants.LUNAR_ECLIPSE_SCALE_FACTOR

            # 月・地球の本影の角距離の計算
            s = abs(np.rad2deg(ephem.separation(sun, moon)) - 180) * 3600

            # 食分の計算
            magnitude = (R_u + r_m - s) / (r_m * 2)

            # 計算結果を追加（時刻、食分）
            res.append([obs.date, magnitude])

        # 食の最大の検索
        max_eclipse = max(res, key=itemgetter(1))
        max_date  = max_eclipse[0]
        magnitude = max_eclipse[1]
        begin_date = None
        end_date = None

        # 欠け始めと食の終わりの検索
        eclipse = False
        for x in res:
            if x[1] > 0 :
                if eclipse == False:
                    begin_date = x[0]
                    eclipse = True
            else :
                if eclipse == True:
                    end_date = x[0]
                    eclipse = False

        return max_date, magnitude, begin_date, end_date
