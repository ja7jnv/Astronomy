import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# .envファイルをロード（同階層にある.envを探して読み込む）
load_dotenv()

def get_weather_forecast(latitude, longitude, api_key):
    """
    緯度と経度を基にOpenWeatherMapから天気予報を取得する
    :param latitude: 緯度
    :param longitude: 経度
    :param api_key: OpenWeatherMapのAPIキー
    :return: 予報データのリスト
    """
    # 5 Day / 3 Hour Forecast APIのエンドポイント
    #endpoint = "https://api.openweathermap.org/data/2.5/weather"   # 現在の天気
    endpoint = "https://api.openweathermap.org/data/2.5/forecast"   # 5日間/3時間ごとの予報
    
    # リクエストパラメータ
    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": api_key,
        "units": "metric", # 単位を摂氏（メートル法）に設定
        "lang": "ja"       # 言語を日本語に設定
    }
    
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる
        data = response.json()
        
        # 現時点以降の予報のみを取得
        forecast_list = data.get("list", [])
        
        if not forecast_list:
            print("予報データが見つかりませんでした。")
            return []

        processed_forecast = []
        for forecast in forecast_list:
            # 日時情報を整形
            timestamp = forecast.get("dt")
            if timestamp:
                forecast_time = datetime.fromtimestamp(timestamp)
                
                # 最高気温と最低気温を取得
                main_data = forecast.get("main", {})
                max_temp = main_data.get("temp_max")
                min_temp = main_data.get("temp_min")
                
                # 天気概況を取得
                weather_data = forecast.get("weather", [])
                weather_description = weather_data[0].get("description") if weather_data else "N/A"
                
                processed_forecast.append({
                    "time": forecast_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "weather": weather_description,
                    "max_temp": max_temp,
                    "min_temp": min_temp
                })
        
        return processed_forecast
        
    except requests.exceptions.RequestException as e:
        print(f"APIリクエスト中にエラーが発生しました: {e}")
        return []


if __name__ == "__main__":
    # 環境変数からAPIキーを取得
    # 第2引数はキーが見つからなかった場合のデフォルト値（なくてもOK）
    MY_API_KEY = os.getenv("OPENWEATHER_API_KEY")

    # APIキーが取得できたかチェック
    if not MY_API_KEY:
        print("エラー: APIキーが見つかりません。.envファイルを確認してください。")
        exit()
    
    # 取得したい場所の緯度と経度を指定
    LATITUDE = os.getenv("OBSERVATION_LATITUDE")
    LONGITUDE = os.getenv("OBSERVATION_LONGITUDE")
    if not (LATITUDE and  LONGITUDE):
        print("エラー: 位置情報が見つかりません。.envファイルを確認してください。")
        exit()

    
    forecast_data = get_weather_forecast(LATITUDE, LONGITUDE, MY_API_KEY)
    
    if forecast_data:
        print(f"--- 緯度: {LATITUDE}, 経度: {LONGITUDE} の天気予報 ---")
        for item in forecast_data:
            print(f"日時: {item['time']}, 天気: {item['weather']}, 最高気温: {item['max_temp']}°C, 最低気温: {item['min_temp']}°C")


