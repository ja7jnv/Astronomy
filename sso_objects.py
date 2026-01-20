class KwArg:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"{self.name}={self.value}"


class HereObject:
    def __init__(self, lat=None, lon=None, elev=None):
        self.lat = lat
        self.lon = lon
        self.elev = elev

    def __repr__(self):
        return "Here"

    def show(self):
        print(f"Here.Lat  => {self.lat if self.lat is not None else '_'}")
        print(f"Here.Lon  => {self.lon if self.lon is not None else '_'}")
        print(f"Here.Elev => {self.elev if self.elev is not None else '_'}")


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

