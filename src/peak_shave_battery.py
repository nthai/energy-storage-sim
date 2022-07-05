from batteries import Battery, EnergyHub
from batteries import CONFIG

class PeakShaveBattery(Battery):
    def __init__(self) -> None:
        super().__init__()

    def step(self, pdemand):
        pass

    def get_soc(self):
        return self.soc

    def get_maxsoc(self):
        return self.maxsoc
    
    def _selfdischarge(self):
        self.soc = (1 - self.selfdischarge) * self.soc

    def charge(self, pdemand, tdelta=1):
        '''Use pdemand (or a portion of it) to charge the battery.
        Args:
            - pdemand: power that we want to charge the battery with (in kW)
            - tdelta: the time period during which pdemand is applied to the battery (in h)
        Returns:
            - pcharge: the power that is ultimately used on the battery
            - premain: the remaining power, `pdemand - pcharge`'''

        assert pdemand > 0

        # self-discharge always happens
        self._selfdischarge()

        # check if pdemand exceeds the max charging power
        pcharge = min(self.maxcharge, pdemand)

        # check if charging would exceed max state-of-charge
        if self.etacharge * (pcharge * tdelta) + self.soc > self.maxsoc:
            pcharge = (self.maxsoc - self.soc) / self.etacharge / tdelta

        # charge the battery
        self.soc = self.soc + self.etacharge * (pcharge * tdelta)
        assert self.soc <= self.maxsoc

        # 
        premain = pdemand - pcharge
        return pcharge, premain

    def discharge(self, pdemand, tdelta=1):
        '''Try to discharge pdemand of power from the battery.
        Args:
            - pdemand: the amount of power we need (in kW)
            - tdelta: the time period while we discharge the battery (in h)
        Returns:
            - pdischarge: power used to discharge the battery (in kW)
            - premain: remaining power, `pdemand - pdischarge`
        '''
        assert pdemand > 0

        # self-discharge always happens
        self._selfdischarge()

        pdischarge = min(pdemand, self.maxdischarge)

        if self.soc - self.etadischarge * (pdischarge * tdelta) < self.minsoc:
            pdischarge = (self.soc - self.minsoc) / self.etadischarge / tdelta
        self.soc = self.soc - self.etadischarge * (pdischarge * tdelta)
        assert self.soc >= self.minsoc

        premain = pdemand - pdischarge
        return pdischarge, premain

class PeakShaveLiIonBattery(PeakShaveBattery):
    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def _convert_config(cls):
        super()._convert_config()
        cls.selfdischarge = 1 - ((1 - cls.selfdischarge) ** (1/730))

class PeakShaveFlywheel(PeakShaveBattery):
    def __init__(self) -> None:
        super().__init__()

class PeakShaveSupercapacitor(PeakShaveBattery):
    def __init__(self) -> None:
        super().__init__()

PeakShaveLiIonBattery._load_attributes(CONFIG['LiIonBattery'])
PeakShaveFlywheel._load_attributes(CONFIG['Flywheel'])
PeakShaveSupercapacitor._load_attributes(CONFIG['Supercapacitor'])

class PeakShaveEnergyHub(EnergyHub):
    pass # TODO
