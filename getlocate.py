##
# 現在地（大まかな緯度・経度・標高）を取得
#
import geocoder
import requests

def get_location_info():
    # 1. IPアドレスから現在地を取得
    g = geocoder.ip('me')
    if g.latlng is None:
        return "位置情報が取得できませんでした。"
    
    latitude, longitude = g.latlng
    city = g.city
    country = g.country
    
    # 2. 国土地理院の標高APIで標高を取得
    elevation = -9999
    try:
        # APIのURL (緯度経度を指定)
        url = f"https://cyberjapandata.gsi.go.jp{latitude}&lon={longitude}"
        response = requests.get(url)
        if response.status_code == 200:
            elevation = response.json().get('elevation', -9999)
    except Exception as e:
        print(f"標高取得エラー: {e}")

    return {
        "city": city,
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "elevation": elevation
    }

# 実行
info = get_location_info()
if isinstance(info, dict):
    print(f"国: {info['country']}")
    print(f"市町村: {info['city']}")
    print(f"緯度: {info['latitude']}")
    print(f"経度: {info['longitude']}")
    print(f"標高: {info['elevation']} m")
else:
    print(info)

