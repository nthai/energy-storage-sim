from batteries import Battery, EnergyHub
from batteries import CONFIG


def chop(val, to=0, delta=1e-10):
    if to - delta <= val <= to + delta:
        return to
    else:
        return val

class PeakShaveBattery(Battery):
    def __init__(self) -> None:
        super().__init__()

    def step(self, pdemand):
        raise NotImplementedError("This class does not implement the step function!")

    def reset(self):
        self.soc = 0

    def get_soc(self):
        return self.soc

    def get_maxsoc(self):
        return self.maxsoc
    
    def _selfdischarge(self):
        sdcharge = self.selfdischarge * self.soc
        self.soc = self.soc - sdcharge
        return sdcharge

    def charge(self, pdemand, tdelta=1):
        '''Use pdemand (or a portion of it) to charge the battery.
        Args:
            - pdemand: power that we want to charge the battery with (in kW)
            - tdelta: the time period during which pdemand is applied to the battery (in h)
        Returns:
            - pcharge: the power that is ultimately used on the battery
            - premain: the remaining power, `pdemand - pcharge`
            - sdcharge: the amount of self-discharge'''

        assert pdemand >= 0

        # self-discharge always happens
        sdcharge = self._selfdischarge()

        if pdemand == 0:
            return 0, 0, sdcharge

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
        return pcharge, premain, sdcharge

    def discharge(self, pdemand, tdelta=1):
        '''Try to discharge pdemand of power from the battery.
        Args:
            - pdemand: the amount of power we need (in kW)
            - tdelta: the time period while we discharge the battery (in h)
        Returns:
            - pdischarge: power used to discharge the battery (in kW)
            - premain: remaining power, `pdemand - pdischarge`
            - sdcharge: the amount of self-discharge
        '''
        assert pdemand >= 0

        # self-discharge always happens
        sdcharge = self._selfdischarge()

        if pdemand == 0:
            return 0, 0, sdcharge

        pdischarge = min(pdemand, self.maxdischarge)

        if self.soc - self.etadischarge * (pdischarge * tdelta) < self.minsoc:
            pdischarge = (self.soc - self.minsoc) / self.etadischarge / tdelta
        self.soc = self.soc - self.etadischarge * (pdischarge * tdelta)
        self.soc = chop(self.soc)
        assert self.soc >= self.minsoc

        premain = pdemand - pdischarge
        return pdischarge, premain, sdcharge

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
    def _init_batteries(self):
        for _ in range(self.sucap_cnt):
            self.storages.append(PeakShaveSupercapacitor())
        for _ in range(self.flywh_cnt):
            self.storages.append(PeakShaveFlywheel())
        for _ in range(self.liion_cnt):
            self.storages.append(PeakShaveLiIonBattery())
    
    def charge(self, pdemand, tdelta=1):
        total_charge = 0
        total_selfdischarge = 0
        for battery in self.storages:
            pcharge, pdemand, sdcharge = battery.charge(pdemand, tdelta)
            total_charge += pcharge
            total_selfdischarge += sdcharge
        return total_charge, total_selfdischarge

    def discharge(self, pdemand, tdelta=1):
        total_discharge = 0
        total_selfdischarge = 0
        for battery in self.storages:
            pdischarge, pdemand, sdcharge = battery.discharge(pdemand, tdelta)
            total_discharge += pdischarge
            total_selfdischarge += sdcharge
        return total_discharge, total_selfdischarge

    def get_soc(self):
        '''Returns the total state-of-charge of all batteries (in kWh).'''
        return sum([battery.get_soc() for battery in self.storages])
    
    def get_maxsoc(self):
        '''Returns the total maximum state-of-charge of all batteries (in kWh).'''
        return sum([Battery.get_maxsoc() for battery in self.storages])

    def reset(self):
        for battery in self.storages:
            battery.reset()
