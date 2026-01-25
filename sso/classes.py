"""
このモジュール内のクラスは、すべてUTCで処理する。
JTSや他の地方時は、その変換メソッド以外では一切考慮しない。
"""
import ephem
import math
from datetime import datetime

# システム設定管理クラス（シングルトン的な役割）
class SSOSystemConfig:
    def __init__(self):
        self.tz = 9.0
        self.echo = True

    def set_tz(self, value):
        self.tz = float(value)
        return f"UTCからの時差: +{self.tz:g}"

    def set_echo(self, value):
        # 0, Off, False などをオフとみなす柔軟な処理
        s_val = str(value).lower()
        self.echo = s_val not in ["0", "off", "false"]
        return f"Echo mode: {'On' if self.echo else 'Off'}"

class SSOTime:
    def __init__(self, date_str=None, config=None):
        self.config = config
        tz_offset = config.tz if config else 9.0
        
        if date_str:
            try:
                self.date = ephem.Date(date_str)
            except Exception:
                self.date = ephem.now()
        else:
            self.date = ephem.now()

    def __repr__(self):
        return f"{self.date} (UTC)"

class SSOMountain:
    def __init__(self, lat, lon, elev, name="Mountain"):
        self.lat, self.lon, self.elev, self.name = lat, lon, elev, name
    def __repr__(self):
        return f"{self.name}: (Mountain)\n Lat: {self.lat}\n Lon: {self.lon}\n Elev: {self.elev}"

class SSOObserver:
    def __init__(self, lat=None, lon=None, elev=0, name="Observer"):
        self.name = name
        self.lat, self.lon, self.elev = lat, lon, elev
        self.ephem_obs = ephem.Observer()
        if lat is not None:
            self.ephem_obs.lat, self.ephem_obs.lon = str(lat), str(lon)
            self.ephem_obs.elevation = elev
            # 初期状態は現在時刻(UTC)
            self.ephem_obs.date = ephem.now()

    def set_time(self, sso_time_body=None):
        """
        観測地点の時刻を設定する。
        引数が None なら現在時刻(UTC)に同期する。
        """
        if sso_time_body:
            # SSOTimeオブジェクトが持つUTC時刻をセット
            self.ephem_obs.date = sso_time_body.date
        else:
            # 現在のUTC時刻に同期
            self.ephem_obs.date = ephem.now()

    def __repr__(self):
        return f"(Observer)\n Lat: {self.lat}\n Lon: {self.lon}\n Elev: {self.elev}"

class SSOCalculator:
    @staticmethod
    def observe(observer, target_name, config, mode="Now", context=None):
        """
        config: 時差表示のために必要
        """
        obs = observer.ephem_obs
        
        # 天体取得 (Moon固定ではなく、ephemにあるものを動的に取得)
        try:
            body = getattr(ephem, target_name)()
        except AttributeError:
            return f"Error: Unknown body '{target_name}'"

        body.compute(obs)
        
        def to_deg(rad): return math.degrees(rad)
        
        # 結果表示用のTimeオブジェクト作成ヘルパー
        def make_time(edate): return SSOTime(None, config=config) # 中身を入れ替える
        
        # 実際には SSOTime(edate, config) のように初期化したいが
        # SSOTimeの実装に合わせて日付をセットする
        def format_time(edate):
            t = SSOTime(None, config=config)
            t.date = edate
            return t

        if mode == "Now":
            return (f"{observer.name}:\n 時刻: {format_time(obs.date)}\n"
                    f" 方角: {to_deg(body.az):.2f}°\n 高度: {to_deg(body.alt):.2f}°\n"
                    f" 月齢: {getattr(body, 'phase', '-')}")
        
        if mode in ["Rise", "Set"]:
            try:
                method = obs.next_rising if mode == "Rise" else obs.next_setting
                event_time = method(body)
                return f"{observer.name}:\n {target_name}の{'出' if mode=='Rise' else '没'}: {format_time(event_time)}"
            except ephem.AlwaysUpError:
                return f"{target_name} は沈みません"
            except ephem.NeverUpError:
                return f"{target_name} は昇りません"
        
        return "Unknown Mode"
