"""
画面に出力するフォーマットを行う

"""
import ephem
import math
import numpy as np
from datetime import datetime, timezone, timedelta, time
from typing import Optional, Tuple, Dict, Any
from abc import ABC, abstractmethod
from calculation import CelestialCalculator, EarthCalculator
from classes  import Constants

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BodyPosition:
    """天体の情報を整形して出力するクラス"""
    
    def __init__(self, config):
        self.config = config
    
    def format_position(self, body_name, position_data: Dict[str, float]) -> str:
        """
        位置情報のフォーマット
        
        Args:
            position_data: calculate_current_positionの戻り値
            
        Returns:
            フォーマットされた文字列
m       """
        lines = [
            f"観測日時の{body_name}の情報",
            f"高度  : {position_data['altitude']:.2f}°",
            f"方位  : {position_data['azimuth']:.2f}°",
            f"距離  : {position_data['distance']:.4f} AU"
        ]
        
        if body_name == "月":
            lines.append(f"月齢  : {position_data['age']:.2f}　（観測時）")
            lines.append(f"輝面比: {position_data['phase']:.2f}%")
            lines.append(f"視直径: {position_data['diameter']:.2f} arcmin")

        return "\n".join(lines)
    
    def format_events(
        self, 
        body_name: str,
        rise_data: Tuple, 
        transit_data: Tuple, 
        set_data: Tuple, 
        age: float
    ) -> str:
        """
        出入・南中情報のフォーマット
        
        Args:
            body_name: 天体の名前 "月”とか”太陽”
            rise_data: (出時刻, 方位角)
            transit_data: (南中時刻, 高度)
            set_data: (入時刻, 方位角)
            age: 月齢
            
        Returns:
            フォーマットされた文字列
        """
        logger.debug("MoonPsition: format_event")
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
        
        # 全角文字のズレを補正
        # 足りない分をスペースで埋める
        def pad_fullwidth(text, target_width):
            # 全角を2、半角を1としてカウントして調整する簡易ロジック
            import unicodedata
            w = sum([(2 if unicodedata.east_asian_width(c) in 'FWA' else 1) for c in text])
            return text + ' ' * (target_width - w)

        label_rise = pad_fullwidth(f"{body_name}の出", 10)
        label_transit = pad_fullwidth("南中", 10)
        label_set = pad_fullwidth(f"{body_name}の入", 10)

        lines = [
            f"{body_name}の出入り",
            f"{label_rise}：{rise_str:<26}  方位：{rise_az_str}°",
            f"{label_transit}：{transit_str:<26}  高度：{transit_alt_str}°",
            f"{label_set}：{set_str:<26}  方位：{set_az_str}°"
        ]

        if body_name == "月":
            lines.append(f"月齢  ：{age:.1f}　（月が昇った日の正午）")

        return "\n".join(lines)
    
    def _format_event_time(self, event_time: Optional[Any]) -> str:
        logger.debug(f"_format_event_time: {event_time}")
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


class MoonFormatter(CelestialBodyFormatter):
    """月専用フォーマッター"""
    
    def format(self, observer: ephem.Observer, body: ephem.Moon) -> str:
        """月の情報を整形"""
        # 観測日時
        result = self.format_observation_time(observer)
        
        # 現在位置の計算とフォーマット
        moon = CelestialCalculator(observer, body, self.config)
        position = moon.calculate_current_position()
        
        formatter = BodyPosition(self.config)
        result += formatter.format_position("月", position) + "\n\n"
        
        # 計算開始時刻を設定
        local_midnight = moon.get_local_midnight()

        #local_date = local_midnight.date()
        observer.date = ephem.Date(local_midnight)
        body.compute(observer)
        
        # 月の出・南中・月の入の計算
        rise_data = moon.calculate_rising()
        transit_data = moon.calculate_transit()
        set_data = moon.calculate_setting()
        age = moon.calculate_Moon_noon_age()
        
        # フォーマット
        result += formatter.format_events("月", rise_data, transit_data, set_data, age)
        result += "\n"

        return result


class PlanetFormatter(CelestialBodyFormatter):
    """惑星専用フォーマッター"""

    def format(self, observer: ephem.Observer, body: ephem.Body) -> str:
        """惑星の情報を整形"""
        result = self.format_observation_time(observer)
        
        # 惑星の計算
        planet = CelestialCalculator(observer, body, self.config)
        position = planet.calculate_current_position()
        planet_name = "惑星"
        
        # 観測日時の惑星の情報
        formatter = BodyPosition(self.config)
        result += formatter.format_position(planet_name, position) + "\n"
        
        # 星座
        result += f"星座：{position.get('constellation')}\n"
        
        # 等級（あれば）
        result += f"等級：{position.get('magnitude'):.1f}\n"
        result += "\n"
        
        # 惑星の出入り

        # 計算開始時刻を設定
        local_midnight = planet.get_local_midnight()

        # local_date = local_midnight.date()
        observer.date = ephem.Date(local_midnight)
        body.compute(observer)
        
        # 惑星の出・南中・入の計算
        rise_data = planet.calculate_rising()
        transit_data = planet.calculate_transit()
        set_data = planet.calculate_setting()
        age = None
        
        # 出入り情報を追加
        result += formatter.format_events(planet_name, rise_data, transit_data, set_data, age)
        result += "\n"

        return result


class SunFormatter(CelestialBodyFormatter):
    """太陽専用フォーマッター"""
    
    def format(self, observer: ephem.Observer, body: ephem.Sun) -> str:
        """太陽の情報を整形"""
        result = self.format_observation_time(observer)
        
        # 太陽の計算
        sun = CelestialCalculator(observer, body, self.config)
        position = sun.calculate_current_position()

        formatter = BodyPosition(self.config)
        result += formatter.format_position("太陽", position) + "\n\n"
        
        # 計算開始時刻を設定
        local_midnight = sun.get_local_midnight()

        #local_date = local_midnight.date()
        observer.date = ephem.Date(local_midnight)
        body.compute(observer)
        
        # 日の出・南中・日の入の計算
        rise_data = sun.calculate_rising()
        transit_data = sun.calculate_transit()
        set_data = sun.calculate_setting()
        age = None
        
        # フォーマット
        result += formatter.format_events("日", rise_data, transit_data, set_data, age)
        result += "\n"

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
            ephem.Moon: MoonFormatter,
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


