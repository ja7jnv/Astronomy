"""
sso interpreter : Lark Interpreterを用いたDSL実行エンジン
"""
from lark.visitors import Interpreter
from lark import Token
from classes import (SSOObserver, SSOSystemConfig, Constants)
from formatter  import FormatterFactory
from calculation import (CelestialCalculator, EarthCalculator, SSOCalculator) 
from utility import MoonPhase
from datetime import datetime, timezone
from typing import Any, Optional, Union, List
import numpy as np
import configparser
import ephem

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===== 変数管理クラス =====
class VariableManager:
    
    def __init__(self, config: SSOSystemConfig):
        self.variables = {}
        self.bodies = {}
        self.config = config
    
    def set_variable(self, name: str, value: Any) -> None:
        """変数を設定"""
        self.variables[name] = value
        logger.debug(f"Variable set: {name} = {value}")
    
    def get_variable(self, name: str, default: Any = 0.0) -> Any:
        """変数を取得"""
        value = self.variables.get(name, default)
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
            except AttributeError:
                logger.error(f"No setter method for config: {name}")
                return f"Error: Cannot set {name}"
        
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
        if isinstance(obs, ephem.Observer) and isinstance(target, ephem.Body):
            logger.debug("dispatch_pattern: 1. Observer -> Body")

            obs.date = str(self.config.env.get("Time"))     # 観測日時の設定
            target.compute(obs)

            celestial_body = CelestialCalculator(obs, target, self.config)
            position = celestial_body.calculate_current_position()

            # 観測情報をprint
            print(FormatterFactory.reformat(obs, target, self.config))

            # 観測結果（位置情報）を返す。repl側ではechoを無視する必要がある。
            return position
        
        # パターン2: Observer -> Observer : 距離、仰角計算
        if isinstance(obs, ephem.Observer) and isinstance(target, ephem.Observer):
            logger.debug("dispatch_pattern: 2. Observer -> Observer (distance, alt)")
            return FormatterFactory.reformat(obs, target, self.config)
        
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
        
        # 角距離計算
        sep = ephem.separation(body1, body2)
        
        result = f"角距離: {np.rad2deg(sep):.2f}°"
        return result


# ===== Interpreterクラス =====
class SSOInterpreter(Interpreter):
    
    def __init__(self):
        self.config = SSOSystemConfig()
        self.var_mgr = VariableManager(self.config)
        self.arrow_handler = ArrowOperationHandler(self.config, self.var_mgr)
        
        # 設定ファイル読み込み
        self._load_config()
    
    def _load_config(self) -> None:

        # 観測値の緯度、軽度、及び標高を得る
        def _observer_set(place: str) -> None:
            try:
                lat = ini[place]['lat']
                lon = ini[place]['lon']
                elev = ini[place]['elev']
                setattr(self.config.env[place], "lat", lat)
                setattr(self.config.env[place], "lon", lon)
                setattr(self.config.env[place], "elevation", float(elev))
            except KeyError:
                pass

        try:
            ini = configparser.ConfigParser()
            ini.read('config.ini', encoding='utf-8')
            
            # Here（観測地）の読み込み
            _observer_set('Here')

            # Chokai（観測地：鳥海山）の読み込み
            _observer_set('Chokai')

            # 環境変数の設定
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
    

    # ===== 演算系 =====
    
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
    

    # ===== 関数呼び出し =====
    def funccall(self, tree) -> Any:
        """
        関数呼び出しの処理
        
        Args:
            tree: 構文木
            
        Returns:
            関数の戻り値
        """
        attr = tree.children[0].value
        logger.debug(f"funccall: {attr}")
        
        # 引数の処理
        args = []
        if len(tree.children) > 1:
            child = tree.children[1]
            if hasattr(child, 'data'):
                args = self.visit(child)
        
        # 関数ごとの処理を振り分け
        return self._dispatch_function(attr, args)
    
    def _dispatch_function(self, func_name: str, args: List[Any]) -> Any:
        """
        関数名に応じた処理を振り分け
        
        Args:
            func_name: 関数名
            args: 引数リスト
            
        Returns:
            関数の戻り値
        """
        # Date関数
        if func_name == "Date":
            return self._handle_date_function(args)
        
        # UTC関数
        if func_name == "UTC":
            return self._handle_utc_function(args)
        
        # Now関数
        if func_name == "Now":
            return self.config.SSOEphem("now")
        
        # Observer/Mountain
        if func_name in ["Observer", "Mountain"]:
            return self._handle_location_function(func_name, args)
        
        # Direction:    方位分割数
        if func_name == "Direction":
           self.config.env["Direction"] = int(*args)
           return args
            
        # Phase関数
        if func_name == "Phase":
            return self._handle_phase_function(args)

        # Print関数
        if func_name == "Print":
            print(*args)
            return args
        
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

