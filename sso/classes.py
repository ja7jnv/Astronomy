# classes.py
import ephem
import math
from datetime import datetime, timedelta

# デフォルト設定
DEFAULT_TZ = 9.0

class SSOBase:
    """DSL内で扱う全てのオブジェクトの基底クラス"""
    def __repr__(self):
        return f"<{self.__class__.__name__}>"

class SSONumber(SSOBase):
    def __init__(self, value):
        self.value = float(value)
    def __repr__(self):
        return str(self.value)

class SSOTime(SSOBase):
    """時刻オブジェクト"""
    def __init__(self, ephem_date=None, tz_offset=DEFAULT_TZ):
        self.date = ephem.Date(ephem_date) if ephem_date else ephem.now()
        self.tz = tz_offset

    def __repr__(self):
        d = self.date.datetime() + timedelta(hours=self.tz)
        return d.strftime(f"%Y年%m月%d日%H時%M分%S秒 ({self.tz:+g})")

    def to_ephem(self):
        return self.date

class SSOMountain(SSOBase):
    """山オブジェクト """
    def __init__(self, lat, lon, elev):
        self.lat = lat
        self.lon = lon
        self.elev = elev
        self.name = "Mountain"

    def __repr__(self):
        return f"{self.name}: (Mountain)\n Lat: {self.lat}\n Lon: {self.lon}\n Elev: {self.elev}"

class SSOObserver(SSOBase):
    """観測者オブジェクト """
    def __init__(self, lat=None, lon=None, elev=0, name="Observer"):
        self.name = name
        self.ephem_obs = ephem.Observer()
        if lat is None:
            # 引数なしの場合は問い合わせ 
            try:
                self.lat = float(input("... 緯度 = "))
                self.lon = float(input("... 経度 = "))
                self.elev = float(input("... 標高 = "))
            except ValueError:
                print("数値で入力してください。デフォルト値(0)を使用します。")
                self.lat, self.lon, self.elev = 0, 0, 0
        else:
            self.lat = lat
            self.lon = lon
            self.elev = elev
        
        self._update_ephem()

    def _update_ephem(self):
        self.ephem_obs.lat = str(self.lat)
        self.ephem_obs.lon = str(self.lon)
        self.ephem_obs.elevation = self.elev

    def set_date(self, sso_time):
        self.ephem_obs.date = sso_time.to_ephem()

    def __repr__(self):
        return f"{self.name}: (Observer)\n Lat: {self.lat}\n Lon: {self.lon}\n Elev: {self.elev}"

class SSOCalculator:
    """計算ロジックを集約"""
    @staticmethod
    def observe(observer, target_name, time_obj=None, mode="Now", context_obj=None):
        """
        arrow演算子のロジック
        mode: 'Now', 'Rise', 'Set', 'Zenith', 'Mountain'
        context_obj: Mountainオブジェクトなど
        """
        obs = observer.ephem_obs
        # 時間の設定
        if time_obj:
            obs.date = time_obj.to_ephem()
        else:
            obs.date = ephem.now()

        # 天体の取得
        try:
            body = getattr(ephem, target_name)()
        except AttributeError:
            return f"Error: Unknown body '{target_name}'"

        body.compute(obs)
        
        # 出力用ヘルパー
        def format_deg(rad):
            return str(math.degrees(rad))

        if mode == "Now":
            #  現在時刻の観測
            return (f"{observer.name}:\n"
                    f" 時刻: {SSOTime(obs.date)}\n"
                    f" 方角: {format_deg(body.az)}\n"
                    f" 高度: {format_deg(body.alt)}\n"
                    f" 月齢: {body.phase if hasattr(body, 'phase') else '-'}")

        elif mode in ["Rise", "Set", "Zenith"]:
            #  次回の現象
            try:
                if mode == "Rise":
                    event_time = obs.next_rising(body)
                    label = "出"
                elif mode == "Set":
                    event_time = obs.next_setting(body)
                    label = "没"
                elif mode == "Zenith":
                    event_time = obs.next_transit(body)
                    label = "南中"
                
                # その時刻での計算
                obs.date = event_time
                body.compute(obs)
                
                return (f"{observer.name}:\n"
                        f" {target_name}の{label}: {SSOTime(event_time)}\n"
                        f" 方角:   {format_deg(body.az)}")
            except ephem.AlwaysUpError:
                return f"{target_name} は常に地平線の上にあります"
            except ephem.NeverUpError:
                return f"{target_name} は地平線の下にあります"

        elif mode == "Mountain" and context_obj:
            #  山との重なり (簡易実装: 方角の一致を確認)
            # 実際には山頂の仰角と天体の高度などの複雑な計算が必要ですが、
            # ここではプロンプトの例にある「可能性はありません」のロジックを模倣します。
            
            # 簡易判定: 山の方角を計算
            m_lat = math.radians(context_obj.lat)
            m_lon = math.radians(context_obj.lon)
            o_lat = math.radians(observer.lat)
            o_lon = math.radians(observer.lon)
            
            # 方位角計算 (簡易)
            d_lon = m_lon - o_lon
            y = math.sin(d_lon) * math.cos(m_lat)
            x = math.cos(o_lat) * math.sin(m_lat) - math.sin(o_lat) * math.cos(m_lat) * math.cos(d_lon)
            bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
            
            return (f"{observer.name}:\n"
                    f" 山({context_obj.name})の方位: {bearing:.2f}\n"
                    f" {target_name}が掛かる可能性: (詳細計算未実装のため要確認)")

        return "Unknown Operation"
