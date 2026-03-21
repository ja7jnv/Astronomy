"""
太陽、月、惑星の位置、及び出入りを計算するクラス
地球上の２点間の方角、仰角、及び距離を計算するクラス
天体観測の計算を行うクラス

"""
import ephem
import math
import numpy as np
from datetime import datetime, timezone, timedelta, time
from typing import Optional, Tuple, Dict, Any

from classes import Constants, SSOSystemConfig

import logging
logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Position:
    def __init__(self, 
                 altitude,
                 azimuth,
                 distance=None,
                 rising=None,
                 transit=None,
                 setting=None,
                 magnitude=None,
                 phase=None,
                 age=None,
                 age_noon=None,
                 diameter=None,
                 illumination=None,
                 constellation=None):
         logger.debug(f"Position.__init__: altitude={altitude}, azimuth={azimuth}, distance={distance}, magnitude={magnitude}")

         self.altitude  = altitude
         self.azimuth   = azimuth   
         self.distance  = distance  
         self.rising    = rising
         self.transit   = transit
         self.setting   = setting
         self.magnitude = magnitude 
         self.phase     = phase
         self.age       = age
         self.age_noon  = age_noon
         self.diameter  = diameter
         self.illumination= illumination
         self.constellation = constellation
        
class CelestialCalculator:
    constellation_tbl = {
            # 星座の学名: 星座名（日本語）
            "Aries"     : "おひつじ座 ♈",
            "Taurus"    : "おうし座 ♉",
            "Gemini"    : "ふたご座 ♊",
            "Cancer"    : "かに座 ♋",
            "Leo"       : "しし座 ♌",
            "Virgo"     : "おとめ座 ♍",
            "Libra"     : "てんびん座 ♎",
            "Scorpius"  : "さそり座 ♏",
            "Sagittarius": "いて座 ♐",
            "Capricornus": "やぎ座 ♑",
            "Aquarius"  : "みずがめ座 ♒",
            "Pisces"    : "うお座 ♓"
    }
    
    def __init__(self, observer: ephem.Observer, body: ephem.Body, config):
        logger.debug(f"CelestialCalculator.__init__: observer={observer}, body={body}, config={config}")
        self.observer = observer
        self.body = body
        self.config = config

    def calculate_current_position(self) -> Position:
        logger.debug(f"CelestialCalculator.calculate_current_position: body={self.body.name}")
        self.body.compute(self.observer)        # 観測時の状態を計算
        altitude    = math.degrees(self.body.alt)
        azimuth     = math.degrees(self.body.az)
        distance    = getattr(self.body, 'earth_distance', None)

        # オプション項目の初期化
        magnitude = constellation = phase = age = age_noon = illumination = diameter = None

        match self.body.__class__.__name__:
            case "Moon":
                phase = self.body.phase
                age = self.observer.date - ephem.previous_new_moon(self.observer.date)
                illumination = self.body.moon_phase
                diameter = self.body.size / 60.0  # arcminutes to degrees
            case "Sun":
                diameter = self.body.size / 60.0  # arcminutes to degrees
            case _:
                # 惑星の場合
                if isinstance(self.body, ephem.Planet):
                    magnitude = self.body.mag
                    conste = ephem.constellation(self.body)[1]
                    constellation = self.constellation_tbl.get(conste, conste)
                
        # 出・南中・入の計算（全天体共通）
        #
        # 天文台の基準に合わせるための時刻修正
        save_date = self.observer.date                  # 観測時刻を変更するため一時退避
        local_midnight = self.get_local_midnight()      #
        self.observer.date  = ephem.Date(local_midnight)# 観測時刻を地方時0時に変更 
        self.body.compute(self.observer)

        rising  = self.calculate_rising()
        transit = self.calculate_transit()
        setting = self.calculate_setting()
        age_noon= self.calculate_Moon_noon_age()        # 月の正午月齢
        self.observer.date = save_date                  # 観測日時を元の指定時刻に戻す

        return Position(altitude, azimuth,
               distance = distance,
               rising   = rising,
               transit  = transit,
               setting  = setting,
               magnitude= magnitude,
               phase    = phase,
               age      = age,
               age_noon = age_noon,
               diameter = diameter,
               illumination = illumination,
               constellation = constellation
        )


    def get_local_midnight(self) -> datetime:
        """指定日の現地真夜中の時刻を取得"""
        logger.debug(f"CelestialCalculator.get_local_midnight: observer.date={self.observer.date}")
        tz_offset = timezone(timedelta(hours=float(self.config.env['Tz'])))
        utc_now = self.observer.date.datetime().replace(tzinfo=timezone.utc)
        local_now = utc_now.astimezone(tz_offset)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight.astimezone(timezone.utc)

    def calculate_rising(self) -> Tuple[Optional[Any], Optional[float]]:
        """指定日の出の時刻と方位を計算"""
        logger.debug(f"CelestialCalculator.calculate_rising: body={self.body.name}")
        tz_offset = timezone(timedelta(hours=float(self.config.env['Tz'])))

        try:
            rise_time = self.observer.next_rising(self.body)
            local_rise_dt = rise_time.datetime().astimezone(tz_offset)
            self.observer.date = rise_time
            self.body.compute(self.observer)
            rise_azimuth = math.degrees(self.body.az)
            return rise_time, rise_azimuth

        except ephem.AlwaysUpError:
            logger.info("The body is always up.")
            return Constants.EVENT_ALWAYS_UP, None

        except ephem.NeverUpError:
            logger.info("The body does not rise on this date.")
            return Constants.EVENT_NEVER_UP, None

        except Exception as e:
            logger.error(f"Error calculating rise time: {e}")
            return None, None

    def calculate_transit(self) -> Tuple[Optional[Any], Optional[float]]:
        """指定日の南中の時刻と高度を計算"""
        logger.debug(f"CelestialCalculator.calculate_transit: body={self.body.name}")
        tz_offset = timezone(timedelta(hours=float(self.config.env['Tz'])))

        try:
            transit_time = self.observer.next_transit(self.body)
            local_transit_dt = transit_time.datetime().astimezone(tz_offset)
            self.observer.date = transit_time
            self.body.compute(self.observer)
            transit_altitude = math.degrees(self.body.alt)
            return transit_time, transit_altitude

        except Exception as e:
            logger.error(f"Error calculating transit time: {e}")
            return None, None

    def calculate_setting(self) -> Tuple[Optional[Any], Optional[float]]:
        """指定日の入りの時刻と方位を計算"""
        logger.debug(f"CelestialCalculator.calculate_setting: body={self.body.name}")
        tz_offset = timezone(timedelta(hours=float(self.config.env['Tz'])))

        try:
            set_time = self.observer.next_setting(self.body)
            local_set_dt = set_time.datetime().astimezone(tz_offset)
            self.observer.date = set_time
            self.body.compute(self.observer)
            set_azimuth = math.degrees(self.body.az)
            return set_time, set_azimuth

        except Exception as e:
            logger.error(f"Error calculating set time: {e}")
            return None, None

    def calculate_Moon_noon_age(self):
        """天文台の表示に合わせた正午月齢の計算"""
        logger.debug(f"CelestialCalculator.calculate_Moon_noon_age: observer.date={self.observer.date}")
        TZ_OFFSET = float(self.config.env["Tz"])

        # 12:00(Local) - Tz = 03:00(UTC)   // Tz=9.0の場合
        local_noon_in_utc = datetime.combine(self.observer.date.datetime().date(), time(12)) - timedelta(hours=TZ_OFFSET)
        age = ephem.Date(local_noon_in_utc) - ephem.previous_new_moon(local_noon_in_utc)
        return age



"""
地球上の２点間の方角、仰角、及び距離を計算するクラス

"""
class EarthCalculator:

    def __init__(self, obs1: ephem.Observer, obs2: ephem.Observer):
        logger.debug(f"EarthCalculator.__init__: obs1={obs1}, obs2={obs2}")
        self.obs1 = obs1
        self.obs2 = obs2

    def calculate_direction_distance(self) -> Position:
        """２点間の方角、仰角、及び距離を計算"""
        logger.debug(f"EarthCalculator.calculate_direction_distance: obs1_name={getattr(self.obs1, 'name', 'N/A')}, obs2_name={getattr(self.obs2, 'name', 'N/A')}")

        # 緯度、経度、標高を取得
        lat1, lon1, elev1 = float(self.obs1.lat), float(self.obs1.lon), self.obs1.elev
        lat2, lon2, elev2 = float(self.obs2.lat), float(self.obs2.lon), self.obs2.elev

        # 地球半径 (m)
        R = Constants.EARTH_RADIUS

        # ECEF座標系への変換関数
        def to_ecef(lat, lon, h):
            logger.debug(f"EarthCalculator.calculate_direction_distance.to_ecef: lat={lat}, lon={lon}, h={h}")
            x = (R + h) * math.cos(lat) * math.cos(lon)
            y = (R + h) * math.cos(lat) * math.sin(lon)
            z = (R + h) * math.sin(lat)
            return np.array([x, y, z])

        p1 = to_ecef(lat1, lon1, elev1)
        p2 = to_ecef(lat2, lon2, elev2)

        # ベクトルの差分と距離の計算
        d = p2 - p1
        distance = np.linalg.norm(d)

        # 仰角の計算
        # 観測点1の天頂方向ベクトル
        np_vec = np.array([
            math.cos(lat1) * math.cos(lon1),
            math.cos(lat1) * math.sin(lon1),
            math.sin(lat1)
        ])

        # ベクトルdとup_vecのなす角から仰角を計算
        sin_elev = np.dot(d, np_vec) / distance
        elevation = math.asin(np.clip(sin_elev, -1.0, 1.0))  # ラジアン
        
        # 方位角の計算
        east_vec = np.array([-math.sin(lon1), math.cos(lon1), 0])
        north_vec = np.cross(np_vec, east_vec)

        e_comp = np.dot(d, east_vec)
        n_comp = np.dot(d, north_vec)
        azimuth = math.atan2(e_comp, n_comp)  # ラジアン

        distance_km = distance / 1000.0  # メートルからキロメートルへ変換
        azimuth_deg = math.degrees(azimuth) % 360
        altitude_deg = math.degrees(elevation)

        return Position(altitude_deg,
                        azimuth_deg,
                        distance = distance_km
        )


class SSOCalculator:
    """天体観測の計算を行うクラス"""
    
    @classmethod
    def observe(
        cls, 
        observer: ephem.Observer, 
        target_name: str, 
        config: SSOSystemConfig, 
        mode: str = Constants.MODE_NOW, 
        context=None
    ) -> str:
        """天体を観測
        logger.debug(f"SSOCalculator.observe: target_name={target_name}, mode={mode}")
        
        Args:
            observer: 観測地
            target_name: 天体名
            config: 設定
            mode: 観測モード（Now, Rise, Set）
            context: コンテキスト（未使用）
            
        Returns:
            観測結果の文字列
        """
        # 天体取得
        try:
            body = getattr(ephem, target_name)()
        except AttributeError:
            return f"Error: Unknown body '{target_name}'"
        
        body.compute(observer)
        
        def to_deg(rad: float) -> float:
            logger.debug(f"SSOCalculator.observe.to_deg: rad={rad}")
            return math.degrees(rad)
        
        def format_time(edate):
            logger.debug(f"SSOCalculator.observe.format_time: edate={edate}")
            return config.fromUTC(edate.datetime())
        
        if mode == Constants.MODE_NOW:
            result = f"{observer.name if hasattr(observer, 'name') else 'Observer'}:\n"
            result += f" 時刻: {format_time(observer.date)}\n"
            result += f" 方角: {to_deg(body.az):.2f}°\n"
            result += f" 高度: {to_deg(body.alt):.2f}°\n"
            
            if hasattr(body, 'phase'):
                result += f" 月齢: {getattr(body, 'phase', '-')}"
            
            return result
        
        if mode in [Constants.MODE_RISE, Constants.MODE_SET]:
            try:
                method = observer.next_rising if mode == Constants.MODE_RISE else observer.next_setting
                event_time = method(body)
                event_name = '出' if mode == Constants.MODE_RISE else '没'
                
                return f"{observer.name if hasattr(observer, 'name') else 'Observer'}:\n" \
                       f" {target_name}の{event_name}: {format_time(event_time)}"
                       
            except ephem.AlwaysUpError:
                return f"{target_name} は沈みません"
            except ephem.NeverUpError:
                return f"{target_name} は昇りません"
        
        return "Unknown Mode"

