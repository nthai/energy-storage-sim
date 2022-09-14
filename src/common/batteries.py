from abc import ABC, abstractmethod
import os
from re import L
import yaml
import numpy as np
from .util import chop

CONFIG = None
CONFFILE = '/batteries.yaml'
FILEPATH = os.path.dirname(os.path.abspath(__file__))

print(f'{os.path.basename(__file__)}: loading battery config from {FILEPATH+CONFFILE}...')
with open(FILEPATH+CONFFILE) as configfile:
    CONFIG = yaml.safe_load(configfile)

class Battery(ABC):
    capex = None # USD/kWh
    opex = None # USD/kW/year
    lifetime = None # years
    capacity = None # kWh
    maxcharge = None # kW
    maxdischarge = None # kW
    etacharge = None
    etadischarge = None
    selfdischarge = None # 1/month

    @abstractmethod
    def __init__(self) -> None:
        super().__init__()
        self.soc = 0 # state of charge in kWh

    @classmethod
    def _load_attributes(cls, config):
        print(f'{os.path.basename(__file__)}: Loading config for {cls.__name__}...')
        # print('\n'.join([f'\t{k}: {v}' for k, v in config.items()]))

        cls.capex = config['capital_cost']
        cls.opex = config['operating_cost']
        cls.lifetime = config['lifetime']
        cls.capacity = config['capacity']
        cls.maxcharge = config['maximum_charging_power']
        cls.maxdischarge = config['maximum_discharging_power']
        cls.etacharge = config['charge_efficiency']
        cls.etadischarge = config['discharge_efficiency']
        cls.selfdischarge = config['self_discharge_rate']
        cls.unitmaintenance = config['unit_maintenance_cost']
        cls.minsoc = 0
        cls.maxsoc = cls.capacity

        cls._convert_config()

    @classmethod
    def _convert_config(cls):
        '''Convert config parameters to plain USD and hours where possible.'''
        # normalizing everything to hours
        cls.lifetime = cls.lifetime * 365 * 24

        # capital cost in USD
        cls.capex = cls.capex * cls.capacity

        # operational cost in USD/hour
        cls.opex = cls.opex * cls.capacity / 365 / 24
    
    def reset(self):
        self.soc = 0

    def get_soc(self):
        return self.soc

    def get_maxsoc(self):
        return self.maxsoc

    def charge(self, pdemand, tdelta=1):
        '''Use pdemand (or a portion of it) to charge the battery.
        Args:
            - pdemand: power that we want to charge the battery with (in kW)
            - tdelta: the time period during which pdemand is applied to the battery (in h)

        Returns:
            - pcharge: the power that is ultimately used on the battery
            - premain: the remaining power, `pdemand - pcharge`, we can use
                       this power to charge other batteries
            - sdcharge: the amount of self-discharge
        '''

        assert pdemand >= 0

        # print(type(self).__name__)
        # if isinstance(self, LiIonBattery):
        #     print('Charging LiIonBattery')

        # self-discharge always happens
        sdcharge = self._selfdischarge()

        penalty = 0
        prev_soc = self.soc

        if pdemand == 0:
            return 0, 0, sdcharge, 0

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

        if isinstance(self, LiIonBattery):
            penalty = (prev_soc - self.soc) ** 2

        return pcharge, premain, sdcharge, penalty

    def discharge(self, pdemand, tdelta=1):
        '''Try to discharge pdemand of power from the battery.
        Args:
            - pdemand: the amount of power we need (in kW)
            - tdelta: the time period while we discharge the battery (in h)

        Returns:
            - pdischarge: power used to discharge the battery (in kW), this
                          much energy was subtracted from the battery soc
            - premain: remaining power, `pdemand - pdischarge`, we still
                       need this much energy that we will have to get from
                       somewhere else
            - sdcharge: the amount of self-discharge
        '''
        assert pdemand >= 0

        # self-discharge always happens
        sdcharge = self._selfdischarge()

        penalty = 0
        prev_soc = self.soc

        if pdemand == 0:
            return 0, 0, sdcharge, 0

        pdischarge = min(pdemand / self.etadischarge, self.maxdischarge)

        if self.soc - (pdischarge * tdelta) < self.minsoc:
            pdischarge = (self.soc - self.minsoc) / tdelta
        self.soc = self.soc - (pdischarge * tdelta)
        self.soc = chop(self.soc)
        assert self.soc >= self.minsoc

        premain = chop(pdemand - pdischarge * self.etadischarge)

        if isinstance(self, LiIonBattery):
            penalty += (self.soc - prev_soc) ** 2

        return pdischarge, premain, sdcharge, penalty

    def _selfdischarge(self):
        sdcharge = self.selfdischarge * self.soc
        self.soc = self.soc - sdcharge
        return sdcharge

    def do_nothing(self, tdelta=1):
        sdcharge = self._selfdischarge()
        return 0, 0, sdcharge

    def power_to_max(self) -> float:
        '''Returns the amount of power needed to charge up this battery to
        the max.'''
        return (self.maxsoc - self.soc) / self.etacharge

    def get_capex(self, t):
        '''Get capital expenses for the battery using the formula:
            PrEHC / ELF * C * T
        '''
        return self.capex / self.lifetime * t

    def get_opex(self, t):
        '''Get operational expenses for the battery using the formula:
            PrEHO / UMC * C * T
        '''
        return self.opex / self.unitmaintenance * t

class LiIonBattery(Battery):
    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def _convert_config(cls):
        super()._convert_config()
        cls.selfdischarge = 1 - ((1 - cls.selfdischarge) ** (1/730))

class Flywheel(Battery):
    def __init__(self) -> None:
        super().__init__()

class Supercapacitor(Battery):
    def __init__(self) -> None:
        super().__init__()

LiIonBattery._load_attributes(CONFIG['LiIonBattery'])
Flywheel._load_attributes(CONFIG['Flywheel'])
Supercapacitor._load_attributes(CONFIG['Supercapacitor'])

class EnergyHub:
    def __init__(self, config: dict) -> None:
        '''Initialize energy storage hub containing multiple batteries.
        Args:
            - config: dict containing the following keys:
              {`LiIonBattery`, `Flywheel`, `Supercapacitor`}'''
        
        if __debug__:
            print(f'{os.path.basename(__file__)}: EnergyHub initialized with config: {config}')

        self.liion_cnt = config['LiIonBattery']
        self.flywh_cnt = config['Flywheel']
        self.sucap_cnt = config['Supercapacitor']
        self.storages = [] # type: list[Battery]

        self._init_batteries()

    def _init_batteries(self):
        for _ in range(self.sucap_cnt):
            self.storages.append(Supercapacitor())
        for _ in range(self.flywh_cnt):
            self.storages.append(Flywheel())
        for _ in range(self.liion_cnt):
            self.storages.append(LiIonBattery())

    def charge(self, pdemand, tdelta=1):
        '''Attempts to charge batteries in the storage in order.
        Args:
            - pdemand: demand load in kW, the amount of power we want to store
            - tdelta: time duration for which charging power should be applied
                      (in hour)

        Returns:
            - total amount charged (in kW)
            - total charge lost to self-discharge (in kW)
            - total penalty signal from charging a Li-ion battery
            - the remaining power we could not use to charge the batteries'''

        total_charge = 0
        total_selfdischarge = 0
        total_penalty = 0
        for battery in self.storages:
            pcharge, pdemand, sdcharge, penalty = battery.charge(pdemand, tdelta)
            total_charge += pcharge
            total_selfdischarge += sdcharge
            total_penalty += penalty

        return total_charge, total_selfdischarge, total_penalty, pdemand

    def discharge(self, pdemand, tdelta=1):
        '''Attempts to discharge batteries in the storage in order.
        Args:
            - pdemand: demand load in kW, the amount of power we want to release
            - tdelta: time duration for which charging power should be applied
                      (in hour)

        Returns:
            - total amount discharged (in kW)
            - total charge lost to self-discharge (in kW)
            - total penalty signal from charging a Li-ion battery
            - the remaining power we still need from batteries'''

        total_discharge = 0
        total_selfdischarge = 0
        total_penalty = 0
        for battery in self.storages:
            pdischarge, pdemand, sdcharge, penalty = battery.discharge(pdemand, tdelta)
            total_discharge += pdischarge
            total_selfdischarge += sdcharge
            total_penalty += penalty
        return total_discharge, total_selfdischarge, total_penalty, pdemand

    def do_nothing(self):
        total_selfdischarge = 0
        for battery in self.storages:
            _, _, sdcharge = battery.do_nothing()
            total_selfdischarge += sdcharge
        return 0, 0, total_selfdischarge

    def get_soc(self):
        '''Returns the total state-of-charge of all batteries (in kWh).'''
        return sum(battery.get_soc() for battery in self.storages)
    
    def get_maxsoc(self):
        '''Returns the total maximum state-of-charge of all batteries (in kWh).'''
        return sum([battery.get_maxsoc() for battery in self.storages])

    def reset(self):
        for battery in self.storages:
            battery.reset()

    def power_to_max(self):
        '''Returns the amount of power necessary to charge the whole ehub to max.'''
        power = 0
        for battery in self.storages:
            power += battery.power_to_max()
        return power

    def compute_reserve_time(self, pnet_list):
        '''Given a list of power demands, computes how much time would we last on
        our batteries only. We assume that the minimum SOC is zero.
        Args:
            - pnet_list: list of power demands
        Returns:
            - hours: how many hours would the batteries last'''
        soc_list = self.save_soc()

        hours = 0
        for pnet in pnet_list:
            self.discharge(pnet)
            if self.get_soc() > 0:
                hours += 1
            else:
                break

        self.load_soc(soc_list)
        return hours
    
    def compute_full_reserve(self, pnet_list):
        '''Given a list of power demands, computes, how long would we last if the
        batteries were full.
        Args:
            - pnet_list: list of power demands
        Returns:
            - hours: '''
        soc_list = self.save_soc()

        for battery in self.storages:
            battery.soc = battery.get_maxsoc()
        hours = self.compute_reserve_time(pnet_list)

        self.load_soc(soc_list)
        return hours

    def find_next_charge_time(self, price_list, treserve):
        '''
        Args:
            - price_list: list of electricity prices
            - treserve: amount of time the energyhub would last if it was full
        '''
        curr_price = price_list[0]
        end = min(len(price_list), treserve + 1)
        min_idx = np.argmin(price_list[:end])
        return min_idx

    def power_until(self, tstep, pnet_list):
        pass

    def get_capex(self, t) -> float:
        return sum([battery.get_capex(t) for battery in self.storages])

    def get_opex(self, t) -> float:
        return sum([battery.get_opex(t) for battery in self.storages])

    def save_soc(self) -> list[float]:
        soc_list = []
        for battery in self.storages:
            soc_list.append(battery.soc)
        return soc_list

    def load_soc(self, soc_list: list[float]):
        for idx, battery in enumerate(self.storages):
            battery.soc = soc_list[idx]

def test():
    #TODO
    pass

if __name__ == '__main__':
    test()
