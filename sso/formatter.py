"""
画面に出力するフォーマットを行う

"""
import ephem
import math
import numpy as np
from datetime import datetime, timezone, timedelta, time
from typing import Optional, Tuple, Dict, Any
from abc import ABC, abstractmethod
from calculation import MoonPositionCalculator, MoonEventCalculator, EarthCalculator
from classes  import Constants

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
m       """
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
            f"月齢  ：{age:.1f}　（月が昇った日の正午）"
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

        ec = EarthCalculator(obs1, obs2)
        earth = ec.calculate_direction_distance()

        result = f"2地点間の距離: {earth.get("distance"):.2f} km\n"
        result = result + f"方位角 (Azimuth): {earth.get("azimuth"):.2f}°\n"
        result = result + f"仰角  (Altitude): {earth.get("altitude"):.2f}°\n"
 
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


    @staticmethod
    def reformat(body, target=None, config=None) -> Optional[str]:
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
                    return reformat_observer(body)
                else: # ファクトリーを使って適切なフォーマッターを取得
                    formatter = FormatterFactory.create_formatter(type(target), config or self)
                    return formatter.format(body, target)

            case ephem.Body(): # 天体単体の場合
                formatter = FormatterFactory.create_formatter(type(body), config or self)
                return formatter.format(self.env["Here"], body)

            case _:
                return None


    @staticmethod
    def reformat_observer(body: ephem.Observer) -> str:
        """観測地情報を整形"""
        value = f"\n観測日時：{self.fromUTC(body.date)}"
        value += f"\n緯度：{body.lat}"
        value += f"\n経度：{body.lon}"
        value += f"\n標高：{body.elevation}"
        return value


