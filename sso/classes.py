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
    EARTH_RADIUS = 6378137.0    # 地球半径(m)
    AXIAL_TILT_DEG: 23.439      # 地軸傾斜角(度)
    JULIAN_DAY_J2000: 2451545.0 # J2000.0のユリウス日
    KM_PER_DEGREE_LAT: 111320   # 緯度1度あたりのm
    INTERCARDINAL:  8           # 方位分割 4, 8, 16


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
            "Here"  : ephem.Observer(),
            "Chokai": ephem.Observer()
        }
    
    def set_Tz(self, value: float) -> str:
        """タイムゾーンを設定"""
        self.env["Tz"] = float(value)
        return f"UTCからの時差: +{self.env['Tz']:g}"
    
    @boolean_setter("Echo")
    def set_Echo(self, value):
        """エコーモードを設定"""
        pass
    
    @boolean_setter("Log")
    def set_Log(self, value):
        """ログモードを設定"""
        pass
    
    def set_Here(self, value: ephem.Observer) -> str:
        """デフォルト観測地を設定"""
        self.env["Here"] = value
        return f"Default observer: {self.env['Here']}"
    
    def set_Time(self, value) -> str:
        """観測時刻を設定"""
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
            
            if config:
                self.ephem_obs.date = config.env["Time"]
    
    def __repr__(self) -> str:
        return f"({self.attr})\n Lat: {self.lat}\n Lon: {self.lon}\n Elev: {self.elev}"


