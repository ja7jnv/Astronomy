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
    
    @staticmethod
    def get_8direction(degree):
        """
        方位角(0〜360未満)を8方位の文字列に変換する
        """
        # 360度以上の入力を考慮して調整
        degree = float(degree) % 360

        # 8方位のリスト（北から東回り）
        directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]

        # 360度を8つ(45度ずつ)に分割
        # 各範囲の中心が北(0), 北東(45)になるよう調整
        # (degree + 22.5) / 45 を行うことで、0-45は北、45-90は北東...と判定する
        index = int((degree + 22.5) // 45) % 8

        return directions[index]

    def directions(self, degree, intermediate):
        """
        degree: 0 - <360    方位(°)
        intermediate: 4, 8, 16  方位分割数

        return: 東西南北, 中間方位
        """

        directions_4 = ["北", "東", "南", "西"]
        directions_8 = ["北", "北東", "東", "南東",
                        "南", "南西", "西", "北西"]
        directions_16 = ["北", "北北東", "北東", "東北東",
                         "東", "東南東", "南東", "南南東",
                         "南", "南南西", "南西", "西南西",
                         "西", "西北西", "北西", "北北西"]
        degree = float(degree) % 360
        if intermediate == 4:
            index = int((degree + 45) // 90) % 4
            return directions_4[index]
        elif intermediate == 8:
            index = int((degree + 22.5) // 45) % 8
            return directions_8[index]
        elif intermediate == 16:
            index = int((degree + 11.25) // 22.5) % 16
            return directions_16[index]
        else:
            raise ValueError("intermediate must be 4, 8, or 16")

    def altitude_visible(self, alt: float) -> str:
        match alt:
            case h if h <= 0:                 res = "見えません"
            case h if (h > 0) and (h < 10):   res = "地平線ギリギリに見えます"
            case h if (h >= 10) and (h < 20): res = "地平線近くに見えます"
            case h if h >= 20:                res = "見えます"
            case _: res = ""
        return res

                
    def format_position(self, body_name, position_data: Dict[str, float]) -> str:
        """
        位置情報のフォーマット
        
        Args:
            position_data: calculate_current_positionの戻り値
            
        Returns:
            フォーマットされた文字列
m       """
        az = position_data['azimuth']
        au = "天文単位AU: 太陽と地球の平均距離 1AU ≒ 1.5 億Km"
        al = position_data.get('altitude')
        al_guide = self.altitude_visible(al)

        lines = [ # TODO - 表示桁合わせ必要
            f"[bold gold3]観測日時の{body_name}の情報[/bold gold3]",
            f"方位  : {f'{az:.2f}°':<9}  {self.directions(az,self.config.env.get("Direction", 8))}",
            f"高度  : {f'{al:.2f}°':<9}  {al_guide}",
            f"距離  : {f'{position_data['distance']:.4f} AU':<9}  {au}"
        ]
        
        arcmin = "分角arcmin: 1°= 60 arcmin"

        if body_name == "月":
            age = position_data.get("age", 15.0)
            phase = self._get_moon_phase(age)
            lines.append(f"月齢  : {f'{age:.2f}':<9}  月の形: {phase} [観測時]")
            lines.append(f"輝面比: {f'{position_data['phase']:.2f} %':<9}")
        if body_name in ("月", "太陽"):
            lines.append(f"視直径: {f'{position_data['diameter']:.2f} arcmin':<9}  {arcmin}")

        result = "\n".join(lines)
        return result

    def _get_moon_phase(self, age: float) -> str:
        # 北半球基準の並び
        phase = ('🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘')

        # 周期を1/16（約1.8日）ずらして、各状態が期間の中央に来るように調整
        # これにより、満月の瞬間(14.7日前後)にしっかり「🌕」が表示される
        step = Constants.LUNAR_CYCLE / 8
        offset = step / 2
        idx = int((age + offset) % Constants.LUNAR_CYCLE // step)

        return phase[idx]
    
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
            f"[bold gold3]{body_name}の出入り[/bold gold3]",
            f"{label_rise}：{rise_str:<26}    方位：{rise_az_str}° [{self.directions(rise_az,self.config.env.get("Direction", 8))}]",
            f"{label_transit}：{transit_str:<26}    高度：{transit_alt_str}°",
            f"{label_set}：{set_str:<26}    方位：{set_az_str}° [{self.directions(set_az,self.config.env.get("Direction", 8))}]"
        ]

        if body_name == "月":
            phase = self._get_moon_phase(age)
            lines.append(f"月齢      : {age:.1f}     月の形: {phase} [正午]")

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

        色情報：$ python -m rich.color
        """
        pass
    
    def format_observation_time(self, observer: ephem.Observer) -> str:
        """観測日時の共通フォーマット"""
        result =  f"観測日時：{self.config.fromUTC(observer.date)}\n"
        result += f"観測地　：緯度={observer.lat}  経度={observer.lon}  標高={observer.elevation:.1f} m\n\n"

        return result


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
    planet = {
        "Mercury"   :   "水星",
        "Venus"     :   "金星",
        "Earth"     :   "地球",
        "Mars"      :   "火星",
        "Jupiter"   :   "木星",
        "Saturn"    :   "土星",
        "Uranus"    :   "天王星",
        "Neptune"   :   "海王星",
        "Pluto"     :   "冥王星"
    }

    def format(self, observer: ephem.Observer, body: ephem.Body) -> str:
        """惑星の情報を整形"""
        result = self.format_observation_time(observer)
        
        # 惑星の計算
        planet = CelestialCalculator(observer, body, self.config)
        position = planet.calculate_current_position()
        planet_eng = getattr(body, 'name')
        planet_name = self.planet.get(planet_eng, planet_eng)
        
        # 観測日時の惑星の情報
        formatter = BodyPosition(self.config)
        result += formatter.format_position(planet_name, position) + "\n"
        
        # 星座
        result += f"星座  : [light_slate_blue]{position.get('constellation')}[/light_slate_blue] にいます\n"
        
        # 等級（あれば）
        mag = position.get('magnitude')
        mag_guide = self._get_magnitude_guideline(mag)
        result += f"等級  : {position.get('magnitude'):.1f}  {mag_guide}\n"
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

    # 等級ガイドラインの編集
    def _get_magnitude_guideline(self, mag:float) ->str:
        match int(mag):
            case n if n < 0: res = "[bold bright_white]非常に明るい[/bold bright_white]"
            case 0: res = "[bright_white]非常に明るい[/bright_white]"
            case 1: res = "[bright_white]街なかでも確認可能[/bright_white]"
            case 2: res = "[white]街なかではなんとか見える[/white]"
            case 3: res = "[gray62]街なかでは見えづらい[/gray62]"
            case 4: res = "[gray50]郊外の暗い空で見えるレベル[/gray50]"
            case 5: res = "[gray42]郊外の暗い空でも見えづらい[/gray42]"
            case 6: res = "[gray30]肉眼で見える限界の明るさ[/gray30]"
            case _: res = "[gray19]双眼鏡(7×50：9.5 等まで) や望遠鏡が必要[/gray19]"
        return res
        """
        星の等級別 見え方目安
        〜0等星（マイナス含む）： 非常に明るい。シリウス（-1.46等）、カノープスなど。
        1等星： 1等星は全部で21個。都会でも確認可能。オリオン座のベテルギウスなど。
        2〜3等星： 街中では明るい星だけが目立つ。
        4〜5等星： 郊外の暗い空で、星座の形がはっきりとわかるレベル。
        6等星： 肉眼で見える限界の明るさ（限界等級）。満天の星空。
        7等星〜： 双眼鏡（7×50：9.5等まで）や望遠鏡が必要。
        """


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


