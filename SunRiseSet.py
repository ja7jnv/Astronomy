import datetime
import ephem

yuzawa = ephem.Observer()
yuzawa.lat = '39.15329755162878'
yuzawa.lon = '140.49537052244537'
yuzawa.date = datetime.datetime.now(datetime.timezone.utc)

sun= ephem.Sun()

sunrise_utc = yuzawa.next_rising(sun)
sunrise_jst = ephem.localtime(yuzawa.next_rising(sun))

print(f"UTC（世界標準時）: {sunrise_utc}")
print(f"JST（日本標準時）: {sunrise_jst}")

