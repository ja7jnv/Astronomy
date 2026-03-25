"""
sso interpreter : Lark Interpreterを用いたDSL実行エンジン
- 変数管理: VariableManagerクラスで変数、Body、Observerを管理
- 矢印演算子処理: ArrowOperationHandlerクラスで矢印演算子のパターンを処理
"""
from lark.visitors import Interpreter
from lark import Token
from lark import Tree
from classes import (SSOObserver, SSOSystemConfig, Constants)
from classes import SSOEarth
from classes import console
from formatter  import FormatterFactory
from calculation import (CelestialCalculator, EarthCalculator, SSOCalculator) 
from utility import MoonPhase
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Union, List
import numpy as np
import configparser
import ephem
import math
import re

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BreakException(Exception): pass
class ContinueException(Exception): pass

class ReturnException(Exception):
    def __init__(self, value):
        logger.debug(f"ReturnException.__init__: value={value}")
        self.value = value  # return に渡された評価結果


# ===== 変数管理クラス =====
class VariableManager:
    
    def __init__(self, config: SSOSystemConfig):
        logger.debug(f"VariableManager.__init__: config={config}")
        self.variables = {}
        self.bodies = {}
        self.observer = {}
        self.config = config
        self.builtins = {
                "math_e"    : math.e,
                "math_pi"   : math.pi,
                "math_tau"  : math.tau,
                "math_inf"  : math.inf,
                "math_nan"  : math.nan,
        }
    
    def set_variable(self, name: str, value: Any) -> None:
        """変数を設定"""
        self.variables[name] = value
        logger.debug(f"Variable set: {name} = {value}")
    
    def get_variable(self, name: str, default: Any = 0.0) -> Any:
        """変数を取得"""
        if name in self.variables:
            value = self.variables.get(name)
        elif name in self.builtins:
            value = self.builtins.get(name)
        else:
            value = default
        logger.debug(f"Variable get: {name} = {value}")
        return value
    
    def set_body(self, name: str, value: Any) -> Union[str, Any]:
        """
        Bodyを設定
        Args:
            name: Body名
            value: 値
        Returns:
            環境変数の場合は設定結果メッセージ、それ以外は値
        """
        # 環境変数の場合
        if name in self.config.env.keys():
            method_name = f"set_{name}"
            try:
                method = getattr(self.config, method_name)
                result = method(value)
                logger.debug(f"Config set: {name} = {value}")
                return result
            except AttributeError as e:
                return f"Error: Cannot set {name}, {e}"
        
        #  予約語は設定拒否
        if name in Constants.KEYWORD:
            return f"Error: Cannot set Body name={name}"

        # 通常のBody
        self.bodies[name] = value
        logger.debug(f"Body set: {name} = {value}")
        return value
    
    def get_body(self, name: str) -> Any:
        """
        Bodyを取得
        Args:
            name: Body名
        Returns:
            Body、環境変数、またはephemオブジェクト
        """
        # 環境変数
        if name in self.config.env.keys():
            value = self.config.env[name]
            logger.debug(f"Config get: {name} = {value}")
            return value
        
        # Now など特殊な名前
        if name == "Now":
            value = self.config.SSOEphem("now")
            logger.debug(f"Special body get: {name} = {value}")
            return value
        
        # 未登録の場合はephemから取得して登録
        if name not in self.bodies:
            try:
                value = self.config.SSOEphem(name)
                self.bodies[name] = value
                logger.debug(f"Body auto-registered: {name} = {value}")
                return value
            except AttributeError:
                logger.error(f"Unknown body: {name}")
                raise ValueError(f"Unknown body: {name}")
        
        value = self.bodies[name]
        logger.debug(f"Body get: {name} = {value}")
        return value


# ===== 矢印演算子処理クラス =====
class ArrowOperationHandler:
    
    def __init__(self, config: SSOSystemConfig, variable_manager: VariableManager):
        logger.debug(f"ArrowOperationHandler.__init__: variable_manager={variable_manager}, config={config}")
        self.config = config
        self.var_mgr = variable_manager
    
    def execute(self, obs: Any, target: Any) -> str:
        """
        矢印演算子の実行
        Args:
            obs   : 左辺（Observer, Body）
            target: 右辺（Body, Observer）
            1. Observer -> Body[ [Date] ]
            2. Observer -> Observer
            3. Body -> Body
        Returns:
            観測結果オブジェクトCelestialCalculator or EarthCalculator
        """

        # パターン1: Observer -> Body : 標準パターン
        if isinstance(obs, ephem.Observer) and isinstance(target, (ephem.Body, ephem.PlanetMoon)):

            logger.debug("dispatch_pattern: 1. Observer -> Body")

            # ディフォルトの日付を取得
            default_date = self.config.env.get("Time", self.config.SSOEphem("now"))

            # Observer -> Body[date] で日付指定がある場合はdateを優先
            target_name = getattr(target, "name", "Body")
            obs.date = self.var_mgr.observer.get(target.name, default_date)
            #               ^^^^^^^^^^^^^^^^ここに日付指定が入っている

            celestial_body = CelestialCalculator(obs, target, self.config)
            position = celestial_body.calculate_current_position()

            # 観測情報をprint: TODO - scriptモードを導入するときは考慮
            logger.debug(f"Width: {console.width}, Height: {console.height}")
            console.print(FormatterFactory.reformat(obs, target, position, self.config), crop=False)

            # 観測結果（位置情報）を返す。repl側ではechoを無視する必要がある。
            # TODO - positionだけでなく、rise, transit, set も返したほうがよい
            return position
        
        # パターン2: Observer -> Observer : 距離、仰角計算
        if isinstance(obs, ephem.Observer) and isinstance(target, ephem.Observer):
            logger.debug("dispatch_pattern: 2. Observer -> Observer (distance, alt)")

            earth = EarthCalculator(obs, target)
            position = earth.calculate_direction_distance()

            return FormatterFactory.reformat(obs, target, position, config=self.config)
        
        # パターン3: Body -> body : 距離計算
        if isinstance(obs, ephem.Body) and isinstance(target, ephem.Body):
            logger.debug("dispatch_pattern: 3. Body -> Body (distance)")
            return self._calculate_separation(obs, target)
        
            """    
                # Zenithの場合は特別処理
                if mode == Constants.MODE_ZENITH:
                    return self._handle_zenith(obs, target)
                
                # Rise/Setの場合はSSOCalculatorに委譲
                return SSOCalculator.observe(obs, target, self.config, mode=mode)
            """
 
        # パターン4: Body -> Observer : 食の計算

        # パターン4.1: Sun -> Observer -> Moon : 月食
        # 先ずは太陽から地球を見たオブジェクトを作成
        if isinstance(obs, ephem.Sun) and isinstance(target, ephem.Observer):
            logger.debug(f"dispatch_pattern: 4. Body -> Observer (lunar eclipse)\ntarget:{target}")
            earth = SSOEarth(target)
            earth.sun = obs
            earth.obs = target
            s_date = self.var_mgr.observer.get("Sun", None)     # 検索開始日
            if s_date is not None: earth.obs.date = s_date      # 指定がないときはTime、なければ現時刻
            else: earth.obs.date = self.config.env.get("Time",self.config.SSOEphem("now"))
            logger.debug(f"return: {earth.obs.date}")
            return earth
        #   ↑Sun -> Observer の処理（左結合）終えて
        # ↓３項目の処理 -> Moon
        if isinstance(obs, SSOEarth) and isinstance(target, ephem.Moon):
            logger.debug(f"Lunar eclipse mode")
            obs.moon = target
            period = int(self.var_mgr.observer.get("Moon",5))   # 期間省略時は５年
            #place = self.var_mgr.observer.get("Here","")
            place = next(iter(self.var_mgr.observer.values()), "here")
            res = obs.lunar_eclipse(period, place)

            # zip()関数を使って同時に取り出す
            for d, s, a, stat, x, m, b, e in zip(
                    res.get('date'),        # -> d
                    res.get('separation'),  # -> s
                    res.get('altitude'),    # -> a
                    res.get('status'),      # -> stat
                    res.get("max_time"),    # -> x
                    res.get('magnitude'),   # -> m
                    res.get('begin_time'),  # -> b
                    res.get('end_time')     # -> e
                    ):
                if d is not None: d = self.config.fromUTC(d)
                sx = self._split_date(x)
                sb = self._split_date(b)
                se = self._split_date(e)

                # TODO - 開始時刻の表示がおかしい
                console.print(f"観測日: {d}  観測地: 緯度={str(obs.obs.lat)[:5]} 経度={str(obs.obs.lon)[:6]} 標高={obs.obs.elevation:.1f} m")
                console.print(f"部分食開始:{sb}  最大食:{sx}  部分食終了:{se}")
                console.print(f"状態:{stat}  最大食分:{m:.3f}  高度:{a:.2f}°  離角:{s:.4f}°")
                console.print("")

            return res

        # 非該当の処理
        console.print(f"未サポートの機能: obs={obs}, target={target}")
        return None


    def _split_date(self, val):
        if val is None:
            return None
        val = self.config.fromUTC(val)
        p = val.split(' ')
        return f"{p[1]} {p[2]}"

### 以下日食 ###

        # パターン4.2: Observer -> Moon -> Sun: 日食
        # 先ずは太陽から地球を見たオブジェクトを作成
        if isinstance(obs, SSOEarth) and isinstance(target, ephem.moon):
            logger.debug(f"dispatch_pattern: 4. Observer -> Body (solar eclipse)\ntarget:{target}")
            earth = SSOEarth(target)
            earth.sun = obs
            earth.obs = target
            s_date = self.var_mgr.observer.get("Sun", None)     # 検索開始日
            if s_date is not None: earth.obs.date = s_date      # 指定がないときはTime、なければ現時刻
            else: earth.obs.date = self.config.env.get("Time",self.config.SSOEphem("now"))
            logger.debug(f"return: {earth.obs.date}")
            return earth
        #   ↑Observer -> Moon の処理（左結合）終えて
        # ↓３項目の処理 -> Sun
        if isinstance(obs, ephem.moon) and isinstance(target, ephem.Sun):
            logger.debug(f"Solar eclipse mode")
            """
            日食処理
            """
            res = 0
            console.print("処理ロジックは未")

            return res
        
        # 未対応パターン
        logger.debug(f"dispatch_pattern: Undefine:\nobs:{obs}\ntarget:{target}")
        logger.warning(f"Unsupported arrow operation: {obs} ({mode}) -> {target}")
        return f"Error: Invalid arrow operation {obs} -> {target}"
    
    def _handle_zenith(self, observer: ephem.Observer, target_name: str) -> str:
        """
        天頂（南中）の計算
        Args:
            observer: 観測地
            target_name: 天体名
        Returns:
            南中情報の文字列
        """
        try:
            body = getattr(ephem, target_name)()
            transit_time = observer.next_transit(body)
            
            # 南中時の高度を計算
            observer.date = transit_time
            body.compute(observer)
            
            result = f"南中情報:\n"
            result += f"時刻: {self.config.fromUTC(transit_time.datetime())}\n"
            result += f"高度: {np.rad2deg(body.alt):.2f}°"
            
            return result
            
        except AttributeError:
            return f"Error: Unknown body '{target_name}'"
        except Exception as e:
            logger.error(f"Error calculating zenith: {e}")
            return f"Error: {e}"
    
    def _calculate_separation(self, body1: ephem.Body, body2: ephem.Body) -> str:
        """
        2つの天体間の角距離を計算
        Args:
            body1: 天体1
            body2: 天体2
        Returns:
            角距離の文字列
        """
        # 両方の天体を同じ観測地・時刻で計算
        observer = self.config.env["Here"]
        body1.compute(observer)
        body2.compute(observer)
        
        # 角距離計算 TODO
        #sep = self.config.SSOEphem("separation",body1, body2)
        sep = ephem.separation(body1, body2)
        
        result = f"角距離: {np.rad2deg(sep):.2f}°"
        return result


# ===== Interpreterクラス =====
class SSOInterpreter(Interpreter):
    
    def __init__(self, lark_instance):
        logger.debug(f"SSOInterpreter.__init__: ")
        self.parser = lark_instance  # REPLから受け取ったパーサーを保持
        self.config = SSOSystemConfig()
        self.var_mgr = VariableManager(self.config)
        self.arrow_handler = ArrowOperationHandler(self.config, self.var_mgr)
        # 組み込み関数のマッピング
        self.builtins = {
            "abs"   : abs,
            "round" : round,
            "min"   : min,
            "max"   : max,
            "int"   : int,
            "float" : float,
            "type"  : type,
            "sqrt"  : math.sqrt,
            "exp"   : math.exp,
            "sin"   : math.sin,
            "cos"   : math.cos,
            "tan"   : math.tan,
            "asin"  : math.asin,
            "acos"  : math.acos,
            "atan"  : math.atan,
            "atan2" : math.atan2,
            "log"   : math.log,
            "degrees": math.degrees,
            "radians": math.radians,
            "dist"  : math.dist,
            "pow"   : pow,
            "range" : range,
        }

        # 設定ファイル読み込み
        self._load_config()

        # 関数情報の保持領域
        self.user_functions = {}
    
    def _load_config(self) -> None:

        # 観測値の緯度、軽度、及び標高を得る
        def _observer_set(place: str) -> Any:
            try:
                lat = ini[place]['lat']
                lon = ini[place]['lon']
                elev = ini[place]['elev']
                setattr(self.config.env[place], "lat", lat)
                setattr(self.config.env[place], "lon", lon)
                setattr(self.config.env[place], "elevation", float(elev))
            except KeyError:
                pass

            return self.config.env.get(place, place)
        try:
            ini = configparser.ConfigParser()
            ini.read('config.ini', encoding='utf-8')
            
            # Earthの設定 - 地球の中心を設定
            setattr(self.config.env['Earth'], "lat", 0)
            setattr(self.config.env['Earth'], "lon", 0)
            setattr(self.config.env['Earth'], "elevation", float(-Constants.EARTH_RADIUS))
            
            # Here（観測地）をconfig.iniから読み込んだ値に設定
            self.Home = _observer_set('Here')
            # Here破壊に備えHome変数に退避:Homeコマンドで使用

            # Chokai（観測地：鳥海山）をconfig.iniから読み込んだ値に設定
            _observer_set('Chokai')

            # 環境変数をconfig.iniから読み込んだ値に設定
            self.config.env['Tz'] = float(ini['ENV']['Tz'])
            self.config.env['Log'] = ini['ENV']['Log'].strip('"')
            self.config.env['Echo'] = ini['ENV']['Echo'].strip('"')
            
            logger.info("Config loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    # ===== 代入系 =====
    
    def assign_var(self, tree) -> str:
        """
        変数への代入
        Args:
            tree: 構文木
        Returns:
            代入結果のメッセージ
        """
        name = tree.children[0].value
        expr = self.visit(tree.children[1])
        self.var_mgr.set_variable(name, expr)
        return expr
    
    def assign_body(self, tree) -> str:
        """
        Bodyへの代入
        Args:
            tree: 構文木
        Returns:
            代入結果のメッセージ
        """
        name = tree.children[0].value
        expr = self.visit(tree.children[1])
        result = self.var_mgr.set_body(name, expr)
        return result

    # ===== 倫理演算系 =====

    # --- 論理演算 ---
    """
    def or_op(self, tree):
        # logical_or: logical_or "OR" logical_and
        # 左辺を評価し、真なら右辺を評価せずに短絡評価(Short-circuit)することも可能
        left = self.visit(tree.children[0])
        if left: return True
        return bool(self.visit(tree.children[1]))

    """
    def or_op(self, tree):
        left = self.visit(tree.children[0])
        # tree.children[1] は "OR" トークン
        right = self.visit(tree.children[2])
        return float(left or right)


    """
    def and_and(self, tree):
        # logical_and: logical_and "AND" logical_not
        left = self.visit(tree.children[0])
        if not left: return False
        return bool(self.visit(tree.children[1]))
    """

    def and_and(self, tree):
        left = self.visit(tree.children[0])
        # tree.children[1] は "AND" トークンなので無視
        right = self.visit(tree.children[2])
        return float(left and right)

    """
    def not_op(self, tree):
        # logical_not: "NOT" logical_not
        res = self.visit(tree.children[0])
        return not res
    """

    def not_op(self, tree):
        # children[0] は Token("NOT_OP", "NOT") なので visit しない
        value = self.visit(tree.children[1])
        return float(not value)


    # --- 比較演算 ---
    def compare_op(self, tree):
        logger.debug(f"compare: {tree}")
        # comparison: arrow (">" | "<" | "==" | "!=") arrow
        left = self.visit(tree.children[0])
        op = tree.children[1]  # 演算子文字列
        right = self.visit(tree.children[2])

        logger.debug(f"compare: left={left} op={op} right={right}")

        if   op == ">" : res = left > right
        elif op == "<" : res = left < right
        elif op == "==": res = left == right
        elif op == "!=": res = left != right
        else           : res = False
    
        return float(res)

    """
    Visitorパターンの鉄則:
    Tree オブジェクト: self.visit() に渡して再帰的に処理する。
    Token オブジェクト: 文字列として値を参照する。str(token)
    self.visit() に渡してはいけない。
    """

    # ===== 算術演算系 =====
    
    def arrow_op(self, tree) -> str:
        """
        矢印演算子の処理
        Args:
            tree: 構文木
        Returns:
            演算結果
        """
        logger.debug(tree.pretty())
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        
        return self.arrow_handler.execute(left, right)
    
    def add(self, tree) -> float:
        return self.visit(tree.children[0]) + self.visit(tree.children[1])
    
    def sub(self, tree) -> float:
        return self.visit(tree.children[0]) - self.visit(tree.children[1])
    
    def mul(self, tree) -> float:
        return self.visit(tree.children[0]) * self.visit(tree.children[1])
    
    def div(self, tree) -> float:
        return self.visit(tree.children[0]) / self.visit(tree.children[1])

    def mod(self, tree):
        left = self.visit(tree.children[0])
        right = self.visit(tree.children[1])
        return left % right

    def int_num(self, tree):
        return int(tree.children[0])

    def float_num(self, tree):
        return float(tree.children[0])

    def pow(self, tree) -> float:
        return self.visit(tree.children[0]) ** self.visit(tree.children[1])
    

    # ===== プリミティブ・変数参照 =====
    
    def number(self, tree) -> float:
        """数値リテラル"""
        return float(tree.children[0].value)
    
    def string_literal(self, tree) -> str:
        """文字列リテラル"""
        return tree.children[0].value[1:-1]
    
    def var_load(self, tree) -> Any:
        """変数の読み込み"""
        name = tree.children[0].value
        return self.var_mgr.get_variable(name)
    
    def dot_access(self, tree) -> Any:
        """
        ドットアクセス (var.attr)
        Args:
            tree: 構文木
        Returns:
            属性値
        """
        name = tree.children[0].value
        attr = tree.children[1].value
        
        var = self.var_mgr.get_variable(name, 0.0)
        
        try:
            value = getattr(var, attr, 0)
            logger.debug(f"{name}.{attr} = {value}")
            return value
        except AttributeError:
            logger.error(f"Attribute not found: {name}.{attr}")
            return 0
    
    def body_load(self, tree) -> Any:
        """Bodyの読み込み"""
        name = tree.children[0].value
        return self.var_mgr.get_body(name)
    

    # ===== command呼び出し ===== TODO - 現時点で未実装
    def cmdcall(self, tree) -> Any:
        # コマンド形式の呼び出し
        attr = tree.children[0].value
        logger.debug(f"cmdcall: {attr}")
        
        # 引数の処理
        args = []
        if len(tree.children) > 1:
            child = tree.children[1]
            if hasattr(child, 'data'):
                args = self.visit(child)
        
        # 関数ごとの処理を振り分け
        return self._dispatch_command(attr, args)
    
    def _dispatch_command(self, cmd_name: str, args: List[Any]) -> Any:
        # eclipse 食コマンド
        match cmd_name:
            case "eclipse":
                print(f"command - eclipse: {args}")
                return

    # ===== 補助呼び出し ===== 2026.2.21追加
    def auxcall(self, tree) -> Any:
        aux_name = tree.children[0].value
        logger.debug(f"auxcall: {aux_name}")
        
        # 引数の処理
        args = []
        if len(tree.children) > 1:
            child = tree.children[1]
            if hasattr(child, 'data'):
                args = self.visit(child)

                logger.debug(f"Set auxiliary data of Body: {aux_name} <- {args[0]}")
                self.var_mgr.observer[aux_name] = args[0]
                return self.var_mgr.get_body(aux_name)

    # TODO - return文の位置づけと実装
    # ===== 関数呼び出し =====
    def funccall(self, tree) -> Any:
        func_name = tree.children[0].value
        logger.debug(f"funccall: {func_name}")
        
        # 引数の処理
        args = []
        if len(tree.children) > 1:
            child = tree.children[1]
            if hasattr(child, 'data'):
                args = self.visit(child)

        # 組み込み関数にあるか確認
        if func_name in self.builtins:
            # Pythonの関数を呼び出す（可変長引数 *args で渡す）
            try:
                return self.builtins[func_name](*args)
            except TypeError as e:
                logger.error(f"Function {func_name} argument error: {e}")
                return None

        # SSOユーザ定義関数の処理
        if func_name in self.user_functions:
            return self.execute_user_function(func_name, args)

        # 内部関数ごとの処理を振り分け
        return self._dispatch_function(func_name, args)
    
    def _dispatch_function(self, func_name: str, args: List[Any]) -> Any:
        logger.debug(f"_dispatch_function: func_name={func_name}")
        match func_name  :
            case "Date"  : return self._handle_date_function(args)
            case "UTC"   : return self._handle_utc_function(args)
            case "Now"   : return self.config.SSOEphem("now")
            case  f if f in ["Observer", "Mountain"]:
                return self._handle_location_function(func_name, args)
            case "Home"  : return self._handle_home_function()
            case "Direction":
                direction =int(*args)
                if direction in [4, 8, 16]:
                    self.config.env["Direction"] = int(*args)
                else:
                    raise ValueError(f"Cannot set {direction}. Allowed values are 4, 8, 16.")
                return args
            case "Phase": return self._handle_phase_function(args)
            case "Print": return console.print(args)
            case "print": return console.print(' '.join(map(str,args)))
            case "zone" : return timezone(timedelta(hours=float(*args)))
            case "Solar_eclipse":
                earth = SSOEarth(self.config.env.get("Here"))
                earth.sun = ephem.Sun()
                earth.obs = ephem.Observer()
                s_date = self.var_mgr.observer.get("Sun", None)     # 検索開始日
                if s_date is not None:      # 指定がないときはTime、基本は現時刻
                    earth.obs.date = s_date
                else:
                    earth.obs.date = self.config.env.get("Time",self.config.SSOEphem("now"))
                    logger.debug(f"return: {earth.obs.date}")

                    # argsが空の場合、(5, "world") をデフォルトにする
                    p_list = list(args) + [5, "world"]
                    period = int(p_list[0])
                    place = p_list[1]
                    earth.solar_eclipse([period, place])

            case _      :
                # その他のephem関数
                logger.debug(f"Fundamental ephem call: {func_name}, args={args}")
                return self.config.SSOEphem(func_name, *args)
    
    def _handle_date_function(self, args: List[Any]) -> Any:
        """Date関数の処理"""
        if not args:
            # 対話入力モード
            try:
                year    = int(input("... 年 = "))
                month   = int(input("... 月 = "))
                day     = int(input("... 日 = "))
                hour    = int(input("... 時 = "))
                minute  = int(input("... 分 = "))
                second  = int(input("... 秒 = "))
                
                d_str = f"{year}/{month}/{day} {hour}:{minute}:{second}"
            except (ValueError, EOFError, KeyboardInterrupt):
                logger.info("Date input cancelled, using current time")
                return self.config.SSOEphem("now")
        else:
            d_str = args[0]
        
        logger.debug(f"Date(): d_str={d_str}")
        try:
            utc_dt = self.config.toUTC(d_str)
            return self.config.SSOEphem("Date", utc_dt)
        except Exception as e:
            logger.error(f"Error parsing date: {e}")
            return self.config.SSOEphem("now")
    
    def _handle_utc_function(self, args: List[Any]) -> Any:
        """UTC関数の処理（UTCで直接入力）"""
        if not args:
            # 対話入力モード（UTCとして）
            try:
                year    = int(input("... 年(UTC) = "))
                month   = int(input("... 月(UTC) = "))
                day     = int(input("... 日(UTC) = "))
                hour    = int(input("... 時(UTC) = "))
                minute  = int(input("... 分(UTC) = "))
                second  = int(input("... 秒(UTC) = "))
                
                d_str = f"{year}/{month}/{day} {hour}:{minute}:{second}"
            except (ValueError, EOFError, KeyboardInterrupt):
                logger.info("UTC input cancelled, using current time")
                return self.config.SSOEphem("now")
        else:
            d_str = args[0]
        
        logger.debug(f"UTC(): d_str={d_str}")
        try:
            dt = datetime.strptime(d_str, "%Y/%m/%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc)
            return self.config.SSOEphem("Date", dt)
        except Exception as e:
            logger.error(f"Error parsing UTC date: {e}")
            return self.config.SSOEphem("now")
    
    def _handle_location_function(self, func_name: str, args: List[Any]) -> ephem.Observer:
        """Observer/Mountain関数の処理"""
        logger.debug(f"{func_name} command: args={args}")
        
        if not args:
            # 対話入力モード
            try:
                lat = float(input("... 緯度 = "))
                lon = float(input("... 経度 = "))
                elev = float(input("... 標高 = "))
            except (ValueError, EOFError, KeyboardInterrupt):
                logger.info("Location input cancelled, using default values")
                lat, lon, elev = 0, 0, 0
        else:
            lat, lon, elev = args[0], args[1], args[2] if len(args) > 2 else 0
        
        location = SSOObserver(func_name, lat, lon, elev, config=self.config)
        return location.ephem_obs
    
    def _handle_home_function(self):
        self.config.env["Here"] = self.Home
        return

    def _handle_phase_function(self, args: List[Any]) -> str:
        """Phase関数の処理"""
        if not args:
            return "Error: Phase requires an argument"
        
        # TODO: Matplotlibを使った3Dプロット実装
        obs = args[0]
        moon = args[1]
        phase = MoonPhase(obs, moon)
        phase.draw()

        return

    def execute_user_function(self, func_name, args):
        func_info = self.user_functions[func_name]
        params = func_info["params"]
        block = func_info["block"]
        logger.debug(f"execute_user_function: func_name={func_name}, params={params}, block={block}")

        # 引数の数チェック
        if len(args) != len(params):
            raise TypeError(f"{func_name}() takes {len(params)} arguments but {len(args)} were given")

        # 引数を変数にセット
        # TODO - ※ 現在の変数を一時退避するか、スコープを分けないと外側の変数を壊す
        old_vars = self.var_mgr.variables.copy() # 簡易的な退避（あとでスコープ実装へ）
        for name, val in zip(params, args):
            self.var_mgr.variables[name] = val

        # 実行
        result = None
        try:
            self.visit(block)
        except ReturnException as e:
            result = e.value
        finally:
            # 変数テーブルを元に戻す（簡易スコープ）
            self.var_mgr.variables = old_vars

        return result

    

    # ===== その他 =====
    
    def arglist(self, tree) -> List[Any]:
        """引数リストを評価してリストとして返す"""
        return [self.visit(child) for child in tree.children]
    
    def start(self, tree) -> Optional[Any]:
        """
        開始ノード
        Args:
            tree: 構文木
        Returns:
            最後のstatementの実行結果
        """
        last_result = None
        for child in tree.children:
            res = self.visit(child)
            if not isinstance(res, Token):
                last_result = res
        return last_result


    def f_string(self, tree):
        # tree.children[0] が Token('FSTRING', 'f"..."')
        token_val = str(tree.children[0])
        raw_content = token_val[2:-1] # f" と " を削る
        # 1. 囲みの f" と " を除去
        #raw_content = str(tree.children).strip('f"')

        # 2. {...} 内を解析して置換する関数
        def replace_match(match):
            inner = match.group(1)  # 例: "a:3.2f"

            # 変数名と書式指定子に分ける
            if ":" in inner:
                var_name, fmt = inner.split(":", 1)
                fmt = ":" + fmt  # format関数用に ":" を戻す
            else:
                var_name, fmt = inner, ""

            # 変数テーブルから値を取得
            val = self.var_mgr.variables.get(var_name.strip(), "N/A")

            # Pythonの format 関数に丸投げする (例: format(1.2345, "3.2f"))
            try:
                return format(val, fmt.strip(":"))
            except Exception as e:
                return f"{{Error:{e}}}"

        # 文字列内の {...} をすべて置換
        # パターン: { の後に "}" 以外の文字が続くもの
        result = re.sub(r"\{(.*?)\}", replace_match, raw_content)
        return result


    # ===== 制御構造 =====
    """
    self.visit(tree) は使わない: 
    if_stmt メソッドの中で self.visit(tree) を呼ぶと、無限ループになる。
    必ず子要素 tree.children[n] を指定して visit すること。
    インデックスの確認:
    list index out of range を防ぐため、文法で "IF" などを大文字トークン
    （IF_KWD: "IF"）にしている場合は、それらも children に含まれる。
    真偽判定:
    bool(condition_result) で 0.0 かそれ以外かを判定する。
    """

    def if_stmt(self, tree):

        # tree.children の中身を安全に抽出する
        # Tokenを除外して Tree（式やブロック）だけを取り出す
        nodes = [child for child in tree.children if isinstance(child, Tree)]

        # nodes[0] = 条件式 (expr)
        # nodes[1] = THENブロック
        # nodes[2] = ELSEブロック (存在すれば)

        condition_result = self.visit(nodes[0])

        if bool(condition_result):
            # 真の場合：THENブロックを実行
            return self.visit(nodes[1])
        elif len(nodes) > 2:
            # 偽の場合：ELSEブロックがあれば実行
            return self.visit(nodes[2])

        return None

    def for_stmt(self, tree):
        # 各要素の抽出 (Tokenを除外して Tree か特定の Token を取り出す)
        # tree.children[0] -> VAR_NAME (Token) - 変数名
        # tree.children[1] -> expr (Tree) - 繰り返し対象（リストや範囲）
        # tree.children[2] -> block (Tree) - 実行する中身
        logger.debug(f"tee.children[0] : {tree.children[0]}")
        logger.debug(f"tee.children[1] : {tree.children[1]}")
        logger.debug(f"tee.children[2] : {tree.children[2]}")

        # 名前ベースで安全に取得（インデックスのズレ対策）
        var_name = str(tree.children[0]) # ループ変数名
        iterable_node = tree.children[1] # 繰り返し対象のノード
        block_node = tree.children[2]    # 実行するブロック

        # 繰り返し対象（expr）を評価してリスト等を得る
        # もし expr が range(10) のような関数なら、その戻り値を取得
        items_val = self.visit(iterable_node)

        # items が数値（単一の値）だった場合に備えて、イテラブルに変換するガード
        if isinstance(items_val, (int, float)):
            items = range(int(items_val))
        else:
            items = items_val

        last_result = None

        # Pythonのループで回す
        for value in items:
            # インタープリター内の変数管理（シンボルテーブル）に値をセット
            self.var_mgr.variables[var_name] = float(value)
            try: # ブロックを実行
                last_result = self.visit(block_node)
            except BreakException:
                break
            except ContinueException:
                continue

        return last_result

    def while_stmt(self, tree):
        # children[0]: expr (条件式)
        # children[1]: block (実行内容)
        # ※文法で "while" などをトークン化していない(Treeに含まれない)前提
        condition_node = tree.children[0]
        block_node = tree.children[1]

        last_result = None

        # Python の while を使って、条件が真の間ループさせる
        # self.visit(condition_node) で都度最新の条件結果を評価
        while bool(self.visit(condition_node)):
            try:
                last_result = self.visit(block_node)
            except BreakException:
                break  # Pythonのwhileを抜ける
            except ContinueException:
                continue  # 次の判定へジャンプ

        return last_result


    def block(self, tree):
        last_result = None
        for statement in tree.children:
            # statement が Tree (代入文やprint文など) の場合のみ実行
            if isinstance(statement, Tree):
                res = self.visit(statement)
                # res が [値, "\n"] のリストで返ってくるので、値だけ取り出す
                if isinstance(res, list) and len(res) > 0:
                    last_result = res[0]
                else:
                    last_result = res
            else:
                # Token ("else" や "endif" など) は無視する
                logger.debug(f"Skipping token in block: {statement}")
        return last_result


    def break_stmt(self, tree):
        logger.debug(f"SSOInterpreter.break_stmt: tree={tree}")
        raise BreakException()

    def continue_stmt(self, tree):
        logger.debug(f"SSOInterpreter.continue_stmt: tree={tree}")
        raise ContinueException()

    def return_stmt(self, tree):
        logger.debug(f"SSOInterpreter.return_stmt: tree={tree}")
        # return の後の expr を評価
        value = self.visit(tree.children[0]) if tree.children else None
        raise ReturnException(value)

    def def_stmt(self, tree):
        logger.debug(f"SSOInterpreter.def_stmt: tree={tree}")
        # tree.children[0]: 関数名
        # tree.children[1]: 引数名のリスト (arg_params)
        # tree.children[2]: 実行内容 (block)
        func_name = str(tree.children[0])
        params_node = tree.children[1]
        block_node = tree.children[2]

        # 引数名のリスト化（例: ['x', 'y']）
        param_names = [str(p) for p in params_node.children]

        # ユーザー定義関数テーブルに保存（この時点では visit しない）
        self.user_functions[func_name] = {
            "params": param_names,
            "block": block_node
        }

        return None

    def import_stmt(self, tree):
        logger.debug(f"SSOInterpreter.import_stmt: tree={tree}")
        filename = str(tree.children[0]).strip('"').strip("'")
        logger.debug(f"import path: {filename}")

        try:
            with open(filename, "r", encoding="utf-8") as f:
                code = f.read()

            # self.parser は外部から渡しておくかクラス内に保持しておく必要がある
            if self.parser:
                new_tree = self.parser.parse(code)
                # 現在のインタープリター自身で実行（visit）
                # これにより、このファイル内での def や assign が現在の vm/user_functions に反映される
                return self.visit(new_tree)
            else:
                logger.error("Parser not set in Interpreter. Cannot process import.")
                return None

        except FileNotFoundError:
            logger.error(f"Import file not found: {filename}")
            return None
