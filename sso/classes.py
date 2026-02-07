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
    DEFAULT_ECHO = "Yes"
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


# ===== 月の計算クラス =====
class MoonPositionCalculator:
    """月の位置情報を計算するクラス"""
    
    def __init__(self, observer: ephem.Observer, moon: ephem.Moon, config):
        self.observer = observer
        self.moon = moon
        self.config = config
    
    def calculate_current_position(self) -> Dict[str, float]:
        """
        現在の月の位置を計算
        
        Returns:
            位置情報を含む辞書
        """
        self.moon.compute(self.observer)
        
        return {
            'altitude': math.degrees(self.moon.alt),
            'azimuth': math.degrees(self.moon.az),
            'phase': self.moon.phase,
            'age': self.observer.date - ephem.previous_new_moon(self.observer.date),
            'diameter': self.moon.size / 60.0,  # 秒角->分角にするため60倍
            'distance': self.moon.earth_distance
        }


class MoonEventCalculator:
    """月の出入・南中時刻を計算するクラス"""
    
    def __init__(self, observer: ephem.Observer, moon: ephem.Moon, config):
        self.observer = observer
        self.moon = moon
        self.config = config
        self.tz_offset = timezone(timedelta(hours=float(config.env["Tz"])))
    
    def get_local_midnight(self) -> datetime:
        """
        観測日のローカル時間00:00:00を取得
        
        Returns:
            UTC時刻でのローカル時間の00:00:00
        """
        utc_now = self.observer.date.datetime().replace(tzinfo=timezone.utc)
        local_now = utc_now.astimezone(self.tz_offset)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight.astimezone(timezone.utc)
    
    def calculate_rising(self, local_date: datetime.date) -> Tuple[Optional[Any], Optional[float]]:
        """
        月の出時刻と方位を計算
        
        Args:
            local_date: ローカル時間の日付
            
        Returns:
            (出時刻, 方位角) のタプル
            特殊ケース: (Constants.EVENT_ALWAYS_UP, None) または (Constants.EVENT_NEVER_UP, None)
        """
        try:
            rise_time = self.observer.next_rising(self.moon)
            local_rise_dt = rise_time.datetime().astimezone(self.tz_offset)
            
            ## 日付が変わっていても表示する
            # 日付が変わっていないかチェック
            #if local_rise_dt.date() != local_date:
            #    return None, None
            
            # 方位計算のため再計算
            self.observer.date = rise_time
            self.moon.compute(self.observer)
            
            return rise_time, math.degrees(self.moon.az)
            
        except ephem.AlwaysUpError:
            logger.info("Moon is always up")
            return Constants.EVENT_ALWAYS_UP, None
        except ephem.NeverUpError:
            logger.info("Moon is never up")
            return Constants.EVENT_NEVER_UP, None
        except Exception as e:
            logger.error(f"Error calculating moon rise: {e}")
            return None, None
    
    def calculate_transit(self, local_date: datetime.date) -> Tuple[Optional[Any], Optional[float]]:
        """
        南中時刻と高度を計算
        
        Args:
            local_date: ローカル時間の日付
            
        Returns:
            (南中時刻, 高度) のタプル
        """
        try:
            transit_time = self.observer.next_transit(self.moon)
            local_transit_dt = transit_time.datetime().astimezone(self.tz_offset)
            ## 日付が変わっていても表示する
            #if local_transit_dt.date() != local_date:
            #    return None, None
            
            self.observer.date = transit_time
            self.moon.compute(self.observer)
            
            return transit_time, math.degrees(self.moon.alt)
            
        except Exception as e:
            logger.error(f"Error calculating moon transit: {e}")
            return None, None
    
    def calculate_setting(self, local_date: datetime.date) -> Tuple[Optional[Any], Optional[float]]:
        """
        月の入時刻と方位を計算
        
        Args:
            local_date: ローカル時間の日付
            
        Returns:
            (入時刻, 方位角) のタプル
        """
        try:
            set_time = self.observer.next_setting(self.moon)
            local_set_dt = set_time.datetime().astimezone(self.tz_offset)
            
            ## 日付が変わっていても表示する
            #if local_set_dt.date() != local_date:
            #    return None, None
            
            self.observer.date = set_time
            self.moon.compute(self.observer)
            
            return set_time, math.degrees(self.moon.az)
            
        except Exception as e:
            logger.error(f"Error calculating moon setting: {e}")
            return None, None


class MoonFormatter:
    """月の情報を整形して出力するクラス"""
    
    def __init__(self, config):
        self.config = config
    
    def format_position(self, position_data: Dict[str, float]) -> str:
        """
        位置情報のフォーマット
        
        Args:
            position_data: calculate_current_positionの戻り値
            
        Returns:
            フォーマットされた文字列
        """
        lines = [
            "観測日時の月の情報",
            f"輝面比: {position_data['phase']:.2f}%",
            f"月齢  : {position_data['age']:.2f}　（観測時）",
            f"高度  : {position_data['altitude']:.2f}°  方位: {position_data['azimuth']:.2f}°",
            f"視直径: {position_data['diameter']:.2f} arcmin",
            f"距離  : {position_data['distance']:.4f} AU"
        ]
        return "\n".join(lines)
    
    def format_events(
        self, 
        rise_data: Tuple, 
        transit_data: Tuple, 
        set_data: Tuple, 
        age: float
    ) -> str:
        """
        出入・南中情報のフォーマット
        
        Args:
            rise_data: (出時刻, 方位角)
            transit_data: (南中時刻, 高度)
            set_data: (入時刻, 方位角)
            age: 月齢
            
        Returns:
            フォーマットされた文字列
        """
        rise_time, rise_az = rise_data
        transit_time, transit_alt = transit_data
        set_time, set_az = set_data
        
        # 時刻のフォーマット
        rise_str = self._format_event_time(rise_time)
        transit_str = self._format_event_time(transit_time)
        set_str = self._format_event_time(set_time)
        
        # 方位・高度のフォーマット
        rise_az_str = f"{rise_az:6.2f}" if rise_az is not None else "---"
        transit_alt_str = f"{transit_alt:6.2f}" if transit_alt is not None else "---"
        set_az_str = f"{set_az:6.2f}" if set_az is not None else "---"
        
        lines = [
            "月の出入り",
            f"月の出：{rise_str:<26}  方位：{rise_az_str}°",
            f"南中  ：{transit_str:<26}  高度：{transit_alt_str}°",
            f"月の入：{set_str:<26}  方位：{set_az_str}°",
            f"月齢  ：{age:.1f}　（観測日の正午）"
        ]
        return "\n".join(lines)
    
    def _format_event_time(self, event_time: Optional[Any]) -> str:
        """
        イベント時刻の文字列変換
        
        Args:
            event_time: ephem.Dateまたは特殊な文字列
            
        Returns:
            フォーマットされた時刻文字列
        """
        if event_time is None:
            return "--:-- (なし)"
        elif event_time == Constants.EVENT_ALWAYS_UP:
            return "一日中地平線上"
        elif event_time == Constants.EVENT_NEVER_UP:
            return "一日中地平線下"
        else:
            return self.config.fromUTC(event_time.datetime())


# ===== 継承を用いた天体フォーマッター =====
class CelestialBodyFormatter(ABC):
    """天体情報フォーマッターの抽象基底クラス"""
    
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    def format(self, observer: ephem.Observer, body: ephem.Body) -> str:
        """
        天体情報をフォーマット
        
        Args:
            observer: 観測地
            body: 天体
            
        Returns:
            フォーマットされた文字列
        """
        pass
    
    def format_observation_time(self, observer: ephem.Observer) -> str:
        """観測日時の共通フォーマット"""
        return f"観測日時：{self.config.fromUTC(observer.date)}\n\n"


class MoonFormatterRefactored(CelestialBodyFormatter):
    """月専用フォーマッター（リファクタリング版）"""
    
    def format(self, observer: ephem.Observer, body: ephem.Moon) -> str:
        """月の情報を整形"""
        # 観測日時
        result = self.format_observation_time(observer)
        
        # 現在位置の計算とフォーマット
        position_calc = MoonPositionCalculator(observer, body, self.config)
        position_data = position_calc.calculate_current_position()
        
        formatter = MoonFormatter(self.config)
        result += formatter.format_position(position_data) + "\n\n"
        
        # 出入・南中の計算
        event_calc = MoonEventCalculator(observer, body, self.config)
        
        # 計算開始時刻を設定
        local_midnight = event_calc.get_local_midnight()
        local_date = local_midnight.date()
        observer.date = ephem.Date(local_midnight)
        body.compute(observer)
        
        # 各イベントの計算
        rise_data = event_calc.calculate_rising(local_date)
        transit_data = event_calc.calculate_transit(local_date)
        set_data = event_calc.calculate_setting(local_date)
        
        ## 月齢計算 : 天文台の表示に合わせるため、このロジックは無効
        #sun = ephem.Sun()
        #transit_time = observer.next_transit(sun)
        #utc_noon = transit_time.datetime().replace(tzinfo=timezone.utc)
        #age = observer.date - ephem.previous_new_moon(utc_noon)

        # 天文台の表示に合わせた正午月齢の計算
        TZ_OFFSET = float(self.config.env["Tz"])
        # 12:00(Local) - Tz = 03:00(UTC)   // Tz=9.0の場合
        local_noon_in_utc = datetime.combine(observer.date.datetime().date(), time(12)) - timedelta(hours=TZ_OFFSET)
        age = ephem.Date(local_noon_in_utc) - ephem.previous_new_moon(local_noon_in_utc)
        
        # フォーマット
        result += formatter.format_events(rise_data, transit_data, set_data, age)
        
        return result


class PlanetFormatter(CelestialBodyFormatter):
    """惑星専用フォーマッター"""

    constellation = {
            # 星座の学名: 星座名（日本語）
            "Aries"     : "おひつじ座",
            "Taurus"    : "おうし座",
            "Gemini"    : "ふたご座",
            "Cancer"    : "かに座",
            "Leo"       : "しし座",
            "Virgo"     : "おとめ座",
            "Libra"     : "てんびん座",
            "Scorpius"  : "さそり座",
            "Sagittarius": "いて座",
            "Capricornus": "やぎ座",
            "Aquarius"  : "みずがめ座",
            "Pisces"    : "うお座"
    }
    
    def format(self, observer: ephem.Observer, body: ephem.Body) -> str:
        """惑星の情報を整形"""
        result = self.format_observation_time(observer)
        
        # 惑星の計算
        body.compute(observer)
        
        # 基本情報
        result += "惑星の位置\n"
        result += f"高度：{math.degrees(body.alt):.2f}°\n"
        result += f"方位：{math.degrees(body.az):.2f}°\n"
        
        # 星座
        c = ephem.constellation(body)
        try:
            result += f"星座：{self.constellation[c[1]]}\n"
        except:
            result += f"星座：{c[1]}\n"
        
        # 等級（あれば）
        if hasattr(body, 'mag'):
            result += f"等級：{body.mag:.1f}\n"
        
        return result


class SunFormatter(CelestialBodyFormatter):
    """太陽専用フォーマッター"""
    
    def format(self, observer: ephem.Observer, body: ephem.Sun) -> str:
        """太陽の情報を整形"""
        result = self.format_observation_time(observer)
        
        # 太陽の計算
        body.compute(observer)
        
        # 現在位置
        result += "太陽の位置\n"
        result += f"高度：{math.degrees(body.alt):.2f}°\n"
        result += f"方位：{math.degrees(body.az):.2f}°\n\n"
        
        # 日の出・南中・日の入
        try:
            rise_time = observer.next_rising(body)
            transit_time = observer.next_transit(body)
            set_time = observer.next_setting(body)
            
            result += "太陽の出入り\n"
            result += f"日の出：{self.config.fromUTC(rise_time.datetime())}\n"
            result += f"南中  ：{self.config.fromUTC(transit_time.datetime())}\n"
            result += f"日の入：{self.config.fromUTC(set_time.datetime())}\n"
            
        except Exception as e:
            logger.error(f"Error calculating sun events: {e}")
            result += "太陽の出入り：計算エラー\n"
        
        return result


class earthFormatter(CelestialBodyFormatter):
    """地上フォーマッター"""
    
    def format(self, obs1: ephem.Observer, obs2: ephem.Observer) -> str:
        logger.debug(f"earthForamatter:")
        result = self.format_observation_time(obs1)

        # 1. 緯度・経度・標高の取得（ラジアン変換）
        lat1, lon1, el1 = float(obs1.lat), float(obs1.lon), obs1.elev
        lat2, lon2, el2 = float(obs2.lat), float(obs2.lon), obs2.elev

        # 地球半径 (m)
        R = Constants.EARTH_RADIUS

        # 2. ECEF直交座標系への変換 (x, y, z)
        def to_ecef(lat, lon, h):
            x = (R + h) * math.cos(lat) * math.cos(lon)
            y = (R + h) * math.cos(lat) * math.sin(lon)
            z = (R + h) * math.sin(lat)
            return np.array([x, y, z])

        p1 = to_ecef(lat1, lon1, el1)
        p2 = to_ecef(lat2, lon2, el2)

        # 3. 直線距離 (Slant Range)
        v = p2 - p1
        slant_range = np.linalg.norm(v)

        # 4. 仰角 (Elevation)
        # obs1地点での天頂方向ベクトル (単位ベクトル)
        up_vec = np.array([
            math.cos(lat1) * math.cos(lon1),
            math.cos(lat1) * math.sin(lon1),
            math.sin(lat1)
        ])

        # ベクトルvとup_vecのなす角から仰角を算出
        # sin(elev) = (v・up) / |v|
        sin_elev = np.dot(v, up_vec) / slant_range
        elevation = math.asin(np.clip(sin_elev, -1.0, 1.0))

        # 5. 方角 (Azimuth)
        # 北方向ベクトルと東方向ベクトルを定義
        east_vec = np.array([-math.sin(lon1), math.cos(lon1), 0])
        north_vec = np.cross(up_vec, east_vec)

        e_comp = np.dot(v, east_vec)
        n_comp = np.dot(v, north_vec)
        azimuth = np.arctan2(e_comp, n_comp)    # 戻り値の範囲: (-π,π) の範囲

        distance_km = slant_range / 1000        # meter -> Km
        azimuth = np.degrees(azimuth) % 360     # 負の値を正の環状(0-360)に変換できるらしい： pythonの仕様 例：-90 % 360 -> 270
        altitude = np.degrees(elevation)

        result = f"2地点間の距離: {distance_km:.2f} km\n"
        result = result + f"方位角 (Azimuth): {azimuth:.2f}°\n"
        result = result + f"仰角  (Altitude): {altitude:.2f}°\n"
 
        return result
        
class FormatterFactory:
    """フォーマッター生成ファクトリー"""
    
    @staticmethod
    def create_formatter(body_type: type, config) -> CelestialBodyFormatter:
        """
        天体タイプに応じたフォーマッターを生成
        
        Args:
            body_type: 天体の型
            config: 設定オブジェクト
            
        Returns:
            適切なフォーマッター
        """
        formatters = {
            ephem.Observer: earthFormatter,
            ephem.Moon: MoonFormatterRefactored,
            ephem.Sun: SunFormatter,
            ephem.Mars: PlanetFormatter,
            ephem.Jupiter: PlanetFormatter,
            ephem.Saturn: PlanetFormatter,
            ephem.Venus: PlanetFormatter,
            ephem.Mercury: PlanetFormatter,
            ephem.Uranus: PlanetFormatter,
            ephem.Neptune: PlanetFormatter,
        }
        
        formatter_class = formatters.get(body_type, PlanetFormatter)
        return formatter_class(config)


# ===== システム設定管理クラス =====
class SSOSystemConfig:
    """システム設定管理クラス（リファクタリング版）"""
    
    def __init__(self):
        self.env = {
            "Tz"    : Constants.DEFAULT_TIMEZONE,
            "Echo"  : Constants.DEFAULT_ECHO,
            "Log"   : Constants.DEFAULT_LOG,
            "Time"  : ephem.now(),
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
    
    def SSOEphem(self, attr: str, value=None, config=None):
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
    
    def reformat(self, body, target=None, config=None) -> Optional[str]:
        """
        天体情報を整形
        
        Args:
            body: 観測地または天体
            target: 観測対象の天体（bodyが観測地の場合）
            config: 設定（通常はself）
            
        Returns:
            フォーマットされた文字列
        """
        logger.debug(f"reformat:\nbody:{body}\ntarget:{target}")

        match body:
            case ephem.Observer():
                if target is None:
                    return self.reformat_observer(body)
                else: # ファクトリーを使って適切なフォーマッターを取得
                    formatter = FormatterFactory.create_formatter(type(target), config or self)
                    return formatter.format(body, target)

            case ephem.Body(): # 天体単体の場合
                formatter = FormatterFactory.create_formatter(type(body), config or self)
                return formatter.format(self.env["Here"], body)

            case _:
                return None

    def reformat_observer(self, body: ephem.Observer) -> str:
        """観測地情報を整形"""
        value = f"\n観測日時：{self.fromUTC(body.date)}"
        value += f"\n緯度：{body.lat}"
        value += f"\n経度：{body.lon}"
        value += f"\n標高：{body.elevation}"
        return value


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
        """
        天体を観測
        
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
            return math.degrees(rad)
        
        def format_time(edate):
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
