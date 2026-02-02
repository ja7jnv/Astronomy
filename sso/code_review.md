# 天体観測DSL コードレビューと改善提案

## 概要
Larkを用いた天体観測用インタープリタのコードレビュー結果です。
主に`classes.py`の`reformat_moon`メソッドのモジュール分割と、全体的な設計改善を提案します。

---

## 1. classes.py の改善提案

### 1.1 reformat_moonメソッドの分割

**問題点:**
- `reformat_moon`メソッドが120行以上あり、複数の責務を持っている
- 月の位置計算、出入時刻計算、フォーマット処理が混在
- テストやメンテナンスが困難

**改善案: 責務ごとにクラスを分割**

```python
# 新しいクラス構成

class MoonPositionCalculator:
    """月の位置情報を計算するクラス"""
    
    def __init__(self, observer, moon, config):
        self.observer = observer
        self.moon = moon
        self.config = config
    
    def calculate_current_position(self):
        """現在の月の位置を計算"""
        self.moon.compute(self.observer)
        return {
            'altitude': math.degrees(self.moon.alt),
            'azimuth': math.degrees(self.moon.az),
            'phase': self.moon.phase,
            'age': self.observer.date - ephem.previous_new_moon(self.observer.date),
            'diameter': math.degrees(self.moon.size) * 60.0,
            'distance': self.moon.earth_distance
        }

class MoonEventCalculator:
    """月の出入・南中時刻を計算するクラス"""
    
    def __init__(self, observer, moon, config):
        self.observer = observer
        self.moon = moon
        self.config = config
        self.tz_offset = timezone(timedelta(hours=float(config.env["Tz"])))
    
    def get_local_midnight(self):
        """観測日のローカル時間00:00:00を取得"""
        utc_now = self.observer.date.datetime().replace(tzinfo=timezone.utc)
        local_now = utc_now.astimezone(self.tz_offset)
        local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        return local_midnight.astimezone(timezone.utc)
    
    def calculate_rising(self, local_date):
        """月の出時刻と方位を計算"""
        try:
            rise_time = self.observer.next_rising(self.moon)
            local_rise_dt = rise_time.datetime().astimezone(self.tz_offset)
            
            if local_rise_dt.date() != local_date:
                return None, None
            
            self.observer.date = rise_time
            self.moon.compute(self.observer)
            
            return rise_time, math.degrees(self.moon.az)
            
        except ephem.AlwaysUpError:
            return "AlwaysUp", None
        except ephem.NeverUpError:
            return "NeverUp", None
    
    def calculate_transit(self, local_date):
        """南中時刻と高度を計算"""
        try:
            transit_time = self.observer.next_transit(self.moon)
            local_transit_dt = transit_time.datetime().astimezone(self.tz_offset)
            
            if local_transit_dt.date() != local_date:
                return None, None
            
            self.observer.date = transit_time
            self.moon.compute(self.observer)
            
            return transit_time, math.degrees(self.moon.alt)
            
        except Exception:
            return None, None
    
    def calculate_setting(self, local_date):
        """月の入時刻と方位を計算"""
        try:
            set_time = self.observer.next_setting(self.moon)
            local_set_dt = set_time.datetime().astimezone(self.tz_offset)
            
            if local_set_dt.date() != local_date:
                return None, None
            
            self.observer.date = set_time
            self.moon.compute(self.observer)
            
            return set_time, math.degrees(self.moon.az)
            
        except Exception:
            return None, None

class MoonFormatter:
    """月の情報を整形して出力するクラス"""
    
    def __init__(self, config):
        self.config = config
    
    def format_position(self, position_data):
        """位置情報のフォーマット"""
        lines = [
            "月の高度・方位",
            f"輝面比: {position_data['phase']:.2f}%",
            f"月齢  : {position_data['age']:.2f}",
            f"高度  : {position_data['altitude']:.2f}°  方位: {position_data['azimuth']:.2f}°",
            f"視直径: {position_data['diameter']:.2f} arcmin",
            f"距離  : {position_data['distance']:.4f} AU"
        ]
        return "\n".join(lines)
    
    def format_events(self, rise_data, transit_data, set_data, age):
        """出入・南中情報のフォーマット"""
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
            "月の出入り：",
            f"月の出：{rise_str:<26}  方位：{rise_az_str}°",
            f"南中  ：{transit_str:<26}  高度：{transit_alt_str}°",
            f"月の入：{set_str:<26}  方位：{set_az_str}°",
            f"月齢  ：{age:.1f}"
        ]
        return "\n".join(lines)
    
    def _format_event_time(self, event_time):
        """イベント時刻の文字列変換"""
        if event_time is None:
            return "--:-- (なし)"
        elif event_time == "AlwaysUp":
            return "一日中地平線上"
        elif event_time == "NeverUp":
            return "一日中地平線下"
        else:
            return self.config.fromUTC(event_time.datetime())
```

**リファクタリング後のreformat_moon:**

```python
def reformat_moon(self, obs, moon, config):
    """月の情報を整形（リファクタリング版）"""
    # 観測日時の表示
    result = f"観測日時：{self.fromUTC(obs.date)}\n\n"
    
    # 現在位置の計算とフォーマット
    position_calc = MoonPositionCalculator(obs, moon, config)
    position_data = position_calc.calculate_current_position()
    
    formatter = MoonFormatter(config)
    result += formatter.format_position(position_data) + "\n\n"
    
    # 出入・南中の計算
    event_calc = MoonEventCalculator(obs, moon, config)
    
    # 計算開始時刻を設定
    local_midnight = event_calc.get_local_midnight()
    local_date = local_midnight.date()
    obs.date = ephem.Date(local_midnight)
    moon.compute(obs)
    
    # 各イベントの計算
    rise_data = event_calc.calculate_rising(local_date)
    transit_data = event_calc.calculate_transit(local_date)
    set_data = event_calc.calculate_setting(local_date)
    
    # 月齢計算
    sun = ephem.Sun()
    transit_time = obs.next_transit(sun)
    utc_noon = transit_time.datetime().replace(tzinfo=timezone.utc)
    age = obs.date - ephem.previous_new_moon(utc_noon)
    
    # フォーマット
    result += formatter.format_events(rise_data, transit_data, set_data, age)
    
    return result
```

---

### 1.2 継承を用いた設計改善

**現在の問題:**
- `SSOSystemConfig`が多くの責務を持ちすぎている
- 天体ごとの処理が分散している

**改善案: 基底クラスとサブクラスによる設計**

```python
from abc import ABC, abstractmethod

class CelestialBodyFormatter(ABC):
    """天体情報フォーマッターの抽象基底クラス"""
    
    def __init__(self, config):
        self.config = config
    
    @abstractmethod
    def format(self, observer, body):
        """天体情報をフォーマット"""
        pass
    
    def format_observation_time(self, observer):
        """観測日時の共通フォーマット"""
        return f"観測日時：{self.config.fromUTC(observer.date)}\n\n"

class MoonFormatterRefactored(CelestialBodyFormatter):
    """月専用フォーマッター"""
    
    def format(self, observer, body):
        result = self.format_observation_time(observer)
        
        # 位置情報
        position_calc = MoonPositionCalculator(observer, body, self.config)
        position_data = position_calc.calculate_current_position()
        result += self._format_position(position_data) + "\n\n"
        
        # イベント情報
        event_calc = MoonEventCalculator(observer, body, self.config)
        # ... 以下省略
        
        return result
    
    def _format_position(self, data):
        # 実装
        pass

class PlanetFormatter(CelestialBodyFormatter):
    """惑星専用フォーマッター"""
    
    def format(self, observer, body):
        result = self.format_observation_time(observer)
        
        # 惑星固有の情報
        body.compute(observer)
        result += f"高度：{math.degrees(body.alt):.2f}°\n"
        result += f"方位：{math.degrees(body.az):.2f}°\n"
        
        # 星座の取得
        constellation = ephem.constellation(body)
        result += f"星座：{constellation[1]}\n"
        
        return result

class SunFormatter(CelestialBodyFormatter):
    """太陽専用フォーマッター"""
    
    def format(self, observer, body):
        result = self.format_observation_time(observer)
        
        # 太陽固有の情報（日出・日没など）
        # ... 実装
        
        return result

# ファクトリーパターンで適切なフォーマッターを選択
class FormatterFactory:
    """フォーマッター生成ファクトリー"""
    
    @staticmethod
    def create_formatter(body_type, config):
        formatters = {
            ephem.Moon: MoonFormatterRefactored,
            ephem.Sun: SunFormatter,
            # 惑星は共通処理
            ephem.Mars: PlanetFormatter,
            ephem.Jupiter: PlanetFormatter,
            ephem.Saturn: PlanetFormatter,
            # ... 他の天体
        }
        
        formatter_class = formatters.get(type(body_type), PlanetFormatter)
        return formatter_class(config)

# SSOSystemConfigでの使用
class SSOSystemConfig:
    # ... 既存のコード
    
    def reformat(self, body, target=None, config=None):
        logger.debug(f"reformat:\nbody:{body}\ntarget:{target}")
        
        if isinstance(body, ephem.Observer):
            if target is None:
                return self.reformat_observer(body)
            else:
                # ファクトリーを使って適切なフォーマッターを取得
                formatter = FormatterFactory.create_formatter(target, config or self)
                return formatter.format(body, target)
        
        elif isinstance(body, ephem.Body):
            # 天体単体の場合
            formatter = FormatterFactory.create_formatter(body, config or self)
            return formatter.format(self.env["Here"], body)
        
        return None
```

---

## 2. interpreter.py の改善提案

### 2.1 責務の分離

**問題点:**
- `SSOInterpreter`が構文解析結果の処理と変数管理を両方行っている
- arrow_opメソッドが複雑で理解しにくい

**改善案:**

```python
class VariableManager:
    """変数とBodyの管理を担当"""
    
    def __init__(self, config):
        self.variables = {}
        self.bodies = {}
        self.config = config
    
    def set_variable(self, name, value):
        self.variables[name] = value
    
    def get_variable(self, name, default=0.0):
        return self.variables.get(name, default)
    
    def set_body(self, name, value):
        # 環境変数の場合
        if name in self.config.env.keys():
            method_name = f"set_{name}"
            method = getattr(self.config, method_name)
            return method(value)
        
        self.bodies[name] = value
        return value
    
    def get_body(self, name):
        # 環境変数
        if name in self.config.env.keys():
            return self.config.env[name]
        
        # Now など特殊な名前
        if name == "Now":
            return self.config.SSOEphem("now")
        
        # 未登録の場合はephemから取得
        if name not in self.bodies:
            value = self.config.SSOEphem(name)
            self.bodies[name] = value
            return value
        
        return self.bodies[name]

class ArrowOperationHandler:
    """矢印演算子の処理を担当"""
    
    def __init__(self, config, variable_manager):
        self.config = config
        self.var_mgr = variable_manager
    
    def execute(self, left, right):
        """矢印演算子の実行"""
        # 左辺の解析
        obs, mode = self._parse_left_operand(left)
        target = right
        
        logger.debug(f"Arrow op: {obs} ({mode}) -> {target}")
        
        # 観測日時の設定
        if isinstance(obs, ephem.Observer):
            obs.date = str(self.config.env.get("Time"))
        
        # パターンマッチング
        return self._dispatch_pattern(obs, mode, target)
    
    def _parse_left_operand(self, left):
        """左辺をObserverとModeに分解"""
        if isinstance(left, tuple):
            return left[0], left[1]
        else:
            return left, "Now"
    
    def _dispatch_pattern(self, obs, mode, target):
        """パターンに応じた処理を振り分け"""
        # パターン1: Observer -> Body (現在の状態)
        if isinstance(obs, ephem.Observer) and isinstance(target, ephem.Body) and mode == "Now":
            target.compute(obs)
            return self.config.reformat(obs, target, self.config)
        
        # パターン2: Observer -> Mode (Rise/Set)
        if isinstance(obs, SSOObserver) and target in ["Rise", "Set"]:
            return (obs, target)
        
        # パターン3: (Observer, Mode) -> Target
        if isinstance(obs, ephem.Observer) and isinstance(mode, str) and mode in ["Rise", "Set"]:
            return SSOCalculator.observe(obs, target, self.config, mode=mode)
        
        return f"Error: Invalid arrow operation"

# リファクタリング後のSSOInterpreter
class SSOInterpreter(Interpreter):
    def __init__(self):
        self.config = SSOSystemConfig()
        self.var_mgr = VariableManager(self.config)
        self.arrow_handler = ArrowOperationHandler(self.config, self.var_mgr)
        
        # 設定ファイル読み込み
        self._load_config()
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        ini = configparser.ConfigParser()
        ini.read('config.ini', encoding='utf-8')
        
        lat = ini['Here']['lat']
        lon = ini['Here']['lon']
        elev = ini['Here']['elev']
        
        setattr(self.config.env['Here'], "lat", lat)
        setattr(self.config.env['Here'], "lon", lon)
        setattr(self.config.env['Here'], "elevation", float(elev))
        
        self.config.env['Tz'] = float(ini['ENV']['Tz'])
        self.config.env['Log'] = ini['ENV']['Log'].strip('"')
        self.config.env['Echo'] = ini['ENV']['Echo'].strip('"')
    
    def assign_var(self, tree):
        name = tree.children[0].value
        expr = self.visit(tree.children[1])
        
        self.var_mgr.set_variable(name, expr)
        value = self.config.reformat(expr, config=self.config) or expr
        return f"{name}: {value}"
    
    def assign_body(self, tree):
        name = tree.children[0].value
        expr = self.visit(tree.children[1])
        
        result = self.var_mgr.set_body(name, expr)
        
        # フォーマット済みの結果が返ってくる場合（環境変数）
        if isinstance(result, str) and ": " in result:
            return result
        
        # それ以外の場合はフォーマット
        value = self.config.reformat(expr, config=self.config) or expr
        return f"{name}: {value}"
    
    def arrow_op(self, tree):
        logger.debug(tree.pretty())
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        
        return self.arrow_handler.execute(left, right)
    
    def var_load(self, tree):
        name = tree.children[0].value
        return self.var_mgr.get_variable(name)
    
    def body_load(self, tree):
        name = tree.children[0].value
        return self.var_mgr.get_body(name)
    
    # 以下、他のメソッドは既存のまま
```

---

## 3. 文法の改善提案

### 3.1 未実装機能の提案

文法書を見て、以下の機能が未実装または部分実装です：

#### 3.1.1 Date()の対話入力

```python
# funccallメソッドに追加
def funccall(self, tree):
    attr = tree.children[0].value
    
    # ... 既存のコード
    
    if attr == "Date":
        if not args:
            # 対話入力モード
            try:
                year = int(input("... 年 = "))
                month = int(input("... 月 = "))
                day = int(input("... 日 = "))
                hour = int(input("... 時 = "))
                minute = int(input("... 分 = "))
                second = int(input("... 秒 = "))
                
                d_str = f"{year}/{month}/{day} {hour}:{minute}:{second}"
            except (ValueError, EOFError, KeyboardInterrupt):
                # デフォルトは現在時刻
                d_str = None
        else:
            d_str = args[0]
        
        if d_str:
            utc_dt = self.config.toUTC(d_str)
            return self.config.SSOEphem(attr, utc_dt)
        else:
            return self.config.SSOEphem("now")
```

#### 3.1.2 UTC()関数

```python
# funccallに追加
if attr == "UTC":
    # Date()のUTCバージョン
    if not args:
        # 対話入力
        # ... Dateと同様
        pass
    else:
        # 引数がある場合、それは既にUTC時刻として扱う
        d_str = args[0]
        dt = datetime.strptime(d_str, "%Y/%m/%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return self.config.SSOEphem("Date", dt)
```

#### 3.1.3 Plot()関数（Matplotlib統合）

```python
class MoonPlotter:
    """月の軌道を3D表示"""
    
    def __init__(self, config):
        self.config = config
    
    def plot_trajectory(self, observer, moon, observation_data):
        """月の軌道を3Dプロット"""
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        
        # 出から没までの軌跡を計算
        # ... 実装
        
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        
        # 地平線を円で描画
        # 軌道を描画
        # 現在位置をマーク
        
        plt.show()

# funccallに追加
if attr == "Plot":
    if not args:
        return "Error: Plot requires an argument"
    
    # 引数が観測データの場合
    plotter = MoonPlotter(self.config)
    plotter.plot_trajectory(...)
    return "Plot displayed"
```

#### 3.1.4 Zenith (天頂)サポート

```python
# ArrowOperationHandlerに追加
def _dispatch_pattern(self, obs, mode, target):
    # ... 既存のコード
    
    # Zenith (南中) のサポート
    if mode == "Zenith":
        if isinstance(target, str):
            body = getattr(ephem, target)()
            transit_time = obs.next_transit(body)
            body.compute(obs)
            return f"南中時刻: {self.config.fromUTC(transit_time.datetime())}\n" \
                   f"高度: {math.degrees(body.alt):.2f}°"
    
    # ... 既存のコード
```

#### 3.1.5 天体間の距離計算

```python
# ArrowOperationHandlerに追加
def _dispatch_pattern(self, obs, mode, target):
    # ... 既存のコード
    
    # 天体 -> 天体 (距離)
    if isinstance(obs, ephem.Body) and isinstance(target, ephem.Body):
        # 両方の天体を同じ観測地・時刻で計算
        observer = self.config.env["Here"]
        obs.compute(observer)
        target.compute(observer)
        
        # 簡易的な角距離計算
        sep = ephem.separation(obs, target)
        return f"角距離: {math.degrees(sep):.2f}°"
    
    # ... 既存のコード
```

### 3.2 文法の矛盾点

#### 3.2.1 プロンプトの一貫性

文法書では途中でプロンプトが`>>>`から`sso>`に変わっていますが、実装は`sso>`固定です。
→ 文法書を修正するか、設定可能にする

#### 3.2.2 Echo設定の扱い

```
>>> Echo = off //代入文での値のエコーを止める
```

現在の実装では、`off`は文字列リテラルとして扱われますが、文法書の例では裸の識別子のように見えます。

**提案:** 文法書を以下のように修正
```
>>> Echo = "off" //代入文での値のエコーを止める
```

または、boolean_setterを改良して識別子も受け付ける。

#### 3.2.3 日本語とアルファベットの混在

文法書には日本語のキーワード（月、太陽、惑星など）が登場しますが、現在の文法は英語のみです。

**提案:** 
1. 英語に統一する（現状維持）
2. 日本語のエイリアスを追加する

```python
# 日本語エイリアスのマッピング
JAPANESE_ALIASES = {
    "月": "Moon",
    "太陽": "Sun",
    "火星": "Mars",
    # ... 他の天体
}

# body_loadで変換
def body_load(self, tree):
    name = tree.children[0].value
    # 日本語の場合は英語に変換
    name = JAPANESE_ALIASES.get(name, name)
    # ... 以下既存の処理
```

---

## 4. その他の改善点

### 4.1 エラーハンドリング

現在、多くの場所で例外が`except:`で無条件にキャッチされています。

```python
# 悪い例
except:
    zenith_str = "---"

# 良い例
except ephem.CircumpolarError as e:
    logger.warning(f"Circumpolar body: {e}")
    zenith_str = "周極星"
except Exception as e:
    logger.error(f"Unexpected error in transit calculation: {e}")
    zenith_str = "---"
```

### 4.2 型ヒント

Python 3.10+の機能を活用して型ヒントを追加すると、コードの可読性が向上します。

```python
from typing import Optional, Tuple, Union
import ephem

def reformat_moon(
    self, 
    obs: ephem.Observer, 
    moon: ephem.Moon, 
    config: SSOSystemConfig
) -> str:
    """月の情報を整形"""
    # ...

def calculate_rising(
    self, 
    local_date: datetime.date
) -> Tuple[Optional[ephem.Date], Optional[float]]:
    """月の出時刻と方位を計算"""
    # ...
```

### 4.3 ログの統一

現在、`logger`と`logging`が混在しています。

```python
# classes.pyの150行目
logging.debug(f"reformat_moon:\nobs:{obs}\nmoon:{moon}")

# 他の場所では
logger.debug(f"...")
```

**提案:** すべて`logger`に統一

### 4.4 定数の定義

マジックナンバーや文字列を定数化することで保守性が向上します。

```python
# constants.py (新規作成)

# デフォルト値
DEFAULT_TIMEZONE = 9.0
DEFAULT_ECHO = "Yes"
DEFAULT_LOG = "No"

# イベントモード
MODE_NOW = "Now"
MODE_RISE = "Rise"
MODE_SET = "Set"
MODE_ZENITH = "Zenith"

# 特殊な戻り値
EVENT_ALWAYS_UP = "AlwaysUp"
EVENT_NEVER_UP = "NeverUp"
EVENT_NOT_TODAY = "NotToday"

# フォーマット
TIME_FORMAT_LOCAL = "%Y/%m/%d %H:%M:%S"
TIME_FORMAT_TZ = "%Y/%m/%d %H:%M:%S%z"
```

### 4.5 設定の集約

現在、設定が`config.ini`と`SSOSystemConfig.__init__`の両方にあります。

**提案:** すべての設定を`config.ini`に統一

```ini
[ENV]
Tz = 9.0
Echo = Yes
Log = No
Prompt = sso>

[Here]
lat = 39.15
lon = 140.5
elev = 108

[Display]
DateFormat = %Y/%m/%d %H:%M:%S
AngleFormat = .2f
DistanceFormat = .4f
```

---

## 5. テストの追加

現在テストコードがないため、リファクタリング後の動作保証が困難です。

```python
# tests/test_moon_calculator.py
import unittest
import ephem
from datetime import datetime, timezone
from classes import MoonPositionCalculator, SSOSystemConfig

class TestMoonPositionCalculator(unittest.TestCase):
    
    def setUp(self):
        self.config = SSOSystemConfig()
        self.observer = ephem.Observer()
        self.observer.lat = "35.0"
        self.observer.lon = "139.0"
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
        
        self.assertIn('altitude', result)
        self.assertIn('azimuth', result)
        self.assertIn('phase', result)
        
        # 方位は0-360度の範囲
        self.assertGreaterEqual(result['azimuth'], 0)
        self.assertLessEqual(result['azimuth'], 360)
        
        # 輝面比は0-100%の範囲
        self.assertGreaterEqual(result['phase'], 0)
        self.assertLessEqual(result['phase'], 100)
```

---

## 6. リファクタリングのロードマップ

段階的に実施することを推奨します：

### フェーズ1: 基盤整備（1-2日）
1. 定数ファイルの作成
2. 型ヒントの追加
3. ログの統一
4. エラーハンドリングの改善

### フェーズ2: クラス分割（2-3日）
1. MoonPositionCalculatorの実装
2. MoonEventCalculatorの実装
3. MoonFormatterの実装
4. reformat_moonのリファクタリング

### フェーズ3: 継承構造の導入（2-3日）
1. CelestialBodyFormatterの実装
2. PlanetFormatter、SunFormatterの実装
3. FormatterFactoryの実装
4. SSOSystemConfig.reformatの簡素化

### フェーズ4: Interpreterの改善（2-3日）
1. VariableManagerの実装
2. ArrowOperationHandlerの実装
3. SSOInterpreterのリファクタリング

### フェーズ5: 機能追加（3-5日）
1. 未実装機能の追加（UTC, Plot, Zenithなど）
2. 天体間距離計算の実装
3. 文法の拡張

### フェーズ6: テストとドキュメント（2-3日）
1. ユニットテストの作成
2. 統合テストの作成
3. ドキュメントの整備

---

## 7. まとめ

### 主要な改善点
1. **reformat_moonの分割**: 3つのクラス（Calculator × 2、Formatter）に分割
2. **継承の活用**: 抽象基底クラスとファクトリーパターンの導入
3. **Interpreterの整理**: VariableManagerとArrowOperationHandlerへの責務分離
4. **未実装機能の追加**: UTC, Plot, Zenith, 距離計算など
5. **コード品質**: 型ヒント、エラーハンドリング、定数化

### 期待される効果
- **保守性の向上**: 責務が明確になり、修正箇所が特定しやすい
- **拡張性の向上**: 新しい天体の追加が容易
- **テスト容易性**: 小さなクラスは単体テストが書きやすい
- **可読性の向上**: 構造が整理され、理解しやすい

このリファクタリングを実施することで、より保守性が高く拡張しやすいコードベースになります。
