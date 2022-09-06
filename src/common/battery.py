class IdealBattery:
    def __init__(self) -> None:
        self.soc = 0
        self.minsoc = 0
        self.maxsoc = 1e5 # 100 kW

    def charge(self, power, time=1):
        self.soc += power * time
        self.soc = max(self.minsoc, self.soc)
        self.soc = min(self.maxsoc, self.soc)
