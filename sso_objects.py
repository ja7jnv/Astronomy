class HereObject:
    def __init__(self, lat, lon, elev):
        self.lat = lat
        self.lon = lon
        self.elev = elev

    def __repr__(self):
        return f"Here(lat={self.lat}, lon={self.lon}, elev={self.elev})"


class AltObject:
    def __init__(self, alt):
        self.alt = alt


class ObserverObject:
    def __init__(self, here, alt):
        self.lat = here.lat
        self.lon = here.lon
        self.elev = here.elev + alt

    def __repr__(self):
        return f"Observer(lat={self.lat}, lon={self.lon}, elev={self.elev})"


class MoonObject:
    def __init__(self, when):
        self.when = when

