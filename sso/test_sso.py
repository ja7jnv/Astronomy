"""
天体観測DSLのユニットテスト例

使用方法:
    python -m pytest test_sso.py -v
"""
import unittest
import ephem
from datetime import datetime, timezone
from classes import (
    MoonPositionCalculator,
    MoonEventCalculator,
    MoonFormatter,
    SSOSystemConfig,
    FormatterFactory,
    Constants
)


class TestMoonPositionCalculator(unittest.TestCase):
    """月の位置計算のテスト"""
    
    def setUp(self):
        """テストの前準備"""
        self.config = SSOSystemConfig()
        self.observer = ephem.Observer()
        self.observer.lat = "35.0"
        self.observer.lon = "139.0"
        self.observer.elevation = 0
        self.observer.date = "2026/1/21 00:00:00"
        
        self.moon = ephem.Moon()
        self.calculator = MoonPositionCalculator(
            self.observer, 
            self.moon, 
            self.config
        )
    
    def test_calculate_current_position(self):
        """現在位置の計算テスト"""
        result = self.calculator.calculate_current_position()
        
        # キーの存在確認
        self.assertIn('altitude', result)
        self.assertIn('azimuth', result)
        self.assertIn('phase', result)
        self.assertIn('age', result)
        self.assertIn('diameter', result)
        self.assertIn('distance', result)
        
        # 方位は0-360度の範囲
        self.assertGreaterEqual(result['azimuth'], 0)
        self.assertLessEqual(result['azimuth'], 360)
        
        # 高度は-90〜90度の範囲
        self.assertGreaterEqual(result['altitude'], -90)
        self.assertLessEqual(result['altitude'], 90)
        
        # 輝面比は0-100%の範囲
        self.assertGreaterEqual(result['phase'], 0)
        self.assertLessEqual(result['phase'], 100)
        
        # 月齢は0-30日程度の範囲
        self.assertGreaterEqual(result['age'], 0)
        self.assertLessEqual(result['age'], 31)
        
        # 視直径は妥当な範囲（約29.3-34.1分角）
        self.assertGreater(result['diameter'], 28)
        self.assertLess(result['diameter'], 35)
        
        # 距離は妥当な範囲（約0.0024-0.0027 AU）
        self.assertGreater(result['distance'], 0.002)
        self.assertLess(result['distance'], 0.003)


class TestMoonEventCalculator(unittest.TestCase):
    """月の出入時刻計算のテスト"""
    
    def setUp(self):
        """テストの前準備"""
        self.config = SSOSystemConfig()
        self.observer = ephem.Observer()
        self.observer.lat = "35.0"
        self.observer.lon = "139.0"
        self.observer.elevation = 0
        self.observer.date = "2026/1/21 00:00:00"
        
        self.moon = ephem.Moon()
        self.calculator = MoonEventCalculator(
            self.observer, 
            self.moon, 
            self.config
        )
    
    def test_get_local_midnight(self):
        """ローカル時間の真夜中取得テスト"""
        midnight = self.calculator.get_local_midnight()
        
        # datetimeオブジェクトであることを確認
        self.assertIsInstance(midnight, datetime)
        
        # UTC時刻であることを確認
        self.assertEqual(midnight.tzinfo, timezone.utc)
    
    def test_calculate_rising(self):
        """月の出時刻の計算テスト"""
        local_midnight = self.calculator.get_local_midnight()
        local_date = local_midnight.date()
        
        self.observer.date = ephem.Date(local_midnight)
        self.moon.compute(self.observer)
        
        rise_time, rise_az = self.calculator.calculate_rising(local_date)
        
        # 通常は時刻と方位が返る（またはNone/特殊値）
        if rise_time not in [None, Constants.EVENT_ALWAYS_UP, Constants.EVENT_NEVER_UP]:
            # 方位が妥当な範囲
            self.assertIsNotNone(rise_az)
            self.assertGreaterEqual(rise_az, 0)
            self.assertLessEqual(rise_az, 360)
    
    def test_calculate_transit(self):
        """南中時刻の計算テスト"""
        local_midnight = self.calculator.get_local_midnight()
        local_date = local_midnight.date()
        
        self.observer.date = ephem.Date(local_midnight)
        self.moon.compute(self.observer)
        
        transit_time, transit_alt = self.calculator.calculate_transit(local_date)
        
        # 通常は時刻と高度が返る
        if transit_time is not None:
            self.assertIsNotNone(transit_alt)
            # 高度は-90〜90度
            self.assertGreaterEqual(transit_alt, -90)
            self.assertLessEqual(transit_alt, 90)


class TestMoonFormatter(unittest.TestCase):
    """月の情報フォーマットのテスト"""
    
    def setUp(self):
        """テストの前準備"""
        self.config = SSOSystemConfig()
        self.formatter = MoonFormatter(self.config)
    
    def test_format_position(self):
        """位置情報フォーマットのテスト"""
        position_data = {
            'altitude': 45.5,
            'azimuth': 180.0,
            'phase': 50.5,
            'age': 14.5,
            'diameter': 31.5,
            'distance': 0.0025
        }
        
        result = self.formatter.format_position(position_data)
        
        # 文字列が返ること
        self.assertIsInstance(result, str)
        
        # 必要な情報が含まれること
        self.assertIn('輝面比', result)
        self.assertIn('月齢', result)
        self.assertIn('高度', result)
        self.assertIn('方位', result)
        self.assertIn('視直径', result)
        self.assertIn('距離', result)
        
        # 数値が正しくフォーマットされていること
        self.assertIn('45.5', result)  # 高度
        self.assertIn('180.0', result)  # 方位
        self.assertIn('50.5', result)  # 輝面比
    
    def test_format_event_time_special_cases(self):
        """特殊ケースの時刻フォーマットテスト"""
        # None の場合
        result = self.formatter._format_event_time(None)
        self.assertIn('なし', result)
        
        # AlwaysUp の場合
        result = self.formatter._format_event_time(Constants.EVENT_ALWAYS_UP)
        self.assertIn('地平線上', result)
        
        # NeverUp の場合
        result = self.formatter._format_event_time(Constants.EVENT_NEVER_UP)
        self.assertIn('地平線下', result)


class TestSSOSystemConfig(unittest.TestCase):
    """システム設定のテスト"""
    
    def setUp(self):
        """テストの前準備"""
        self.config = SSOSystemConfig()
    
    def test_initial_values(self):
        """初期値のテスト"""
        self.assertEqual(self.config.env['Tz'], Constants.DEFAULT_TIMEZONE)
        self.assertEqual(self.config.env['Echo'], Constants.DEFAULT_ECHO)
        self.assertEqual(self.config.env['Log'], Constants.DEFAULT_LOG)
    
    def test_set_timezone(self):
        """タイムゾーン設定のテスト"""
        result = self.config.set_Tz(0)
        self.assertEqual(self.config.env['Tz'], 0.0)
        self.assertIn('UTC', result)
        
        result = self.config.set_Tz(-5)
        self.assertEqual(self.config.env['Tz'], -5.0)
    
    def test_set_echo(self):
        """エコーモード設定のテスト"""
        # 文字列での設定
        result = self.config.set_Echo("off")
        self.assertEqual(self.config.env['Echo'], "No")
        
        result = self.config.set_Echo("on")
        self.assertEqual(self.config.env['Echo'], "Yes")
        
        # 数値での設定
        result = self.config.set_Echo(0)
        self.assertEqual(self.config.env['Echo'], "No")
        
        result = self.config.set_Echo(1)
        self.assertEqual(self.config.env['Echo'], "Yes")
    
    def test_utc_conversion(self):
        """UTC変換のテスト"""
        # JST -> UTC
        self.config.env['Tz'] = 9.0
        utc_dt = self.config.toUTC("2026/01/21 12:00:00")
        
        self.assertEqual(utc_dt.hour, 3)  # 12-9 = 3
        self.assertEqual(utc_dt.tzinfo, timezone.utc)
    
    def test_from_utc_conversion(self):
        """UTC -> ローカル時刻変換のテスト"""
        self.config.env['Tz'] = 9.0
        
        utc_str = "2026/01/21 03:00:00"
        local_str = self.config.fromUTC(utc_str)
        
        # JSTに変換されること（+9時間）
        self.assertIn('12:00:00', local_str)
        self.assertIn('[+9', local_str)


class TestFormatterFactory(unittest.TestCase):
    """フォーマッターファクトリーのテスト"""
    
    def setUp(self):
        """テストの前準備"""
        self.config = SSOSystemConfig()
    
    def test_create_moon_formatter(self):
        """月のフォーマッター生成テスト"""
        from classes_refactored import MoonFormatterRefactored
        
        formatter = FormatterFactory.create_formatter(ephem.Moon, self.config)
        self.assertIsInstance(formatter, MoonFormatterRefactored)
    
    def test_create_sun_formatter(self):
        """太陽のフォーマッター生成テスト"""
        from classes_refactored import SunFormatter
        
        formatter = FormatterFactory.create_formatter(ephem.Sun, self.config)
        self.assertIsInstance(formatter, SunFormatter)
    
    def test_create_planet_formatter(self):
        """惑星のフォーマッター生成テスト"""
        from classes_refactored import PlanetFormatter
        
        formatter = FormatterFactory.create_formatter(ephem.Mars, self.config)
        self.assertIsInstance(formatter, PlanetFormatter)
        
        formatter = FormatterFactory.create_formatter(ephem.Jupiter, self.config)
        self.assertIsInstance(formatter, PlanetFormatter)


class TestConstants(unittest.TestCase):
    """定数のテスト"""
    
    def test_constants_exist(self):
        """定数が定義されていることを確認"""
        self.assertEqual(Constants.MODE_NOW, "Now")
        self.assertEqual(Constants.MODE_RISE, "Rise")
        self.assertEqual(Constants.MODE_SET, "Set")
        self.assertEqual(Constants.MODE_ZENITH, "Zenith")
        
        self.assertEqual(Constants.EVENT_ALWAYS_UP, "AlwaysUp")
        self.assertEqual(Constants.EVENT_NEVER_UP, "NeverUp")


if __name__ == '__main__':
    # テストの実行
    unittest.main(verbosity=2)
