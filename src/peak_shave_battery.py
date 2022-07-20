# import numpy as np
# from batteries import Battery, EnergyHub
# from batteries import CONFIG
# from util import chop

# '''
#     Assumptions:
#         - charging power is always enough to charge batteries up to maximum SOC.
# '''

# class PeakShaveBattery(Battery):
#     def __init__(self) -> None:
#         super().__init__()

#     def step(self, pdemand):
#         raise NotImplementedError("This class does not implement the step function!")

#     def reset(self):
#         self.soc = 0

#     def get_soc(self):
#         return self.soc

#     def get_maxsoc(self):
#         return self.maxsoc
    
#     def _selfdischarge(self):
#         sdcharge = self.selfdischarge * self.soc
#         self.soc = self.soc - sdcharge
#         return sdcharge

#     def do_nothing(self, tdelta=1):
#         sdcharge = self._selfdischarge()
#         return 0, 0, sdcharge

#     def charge(self, pdemand, tdelta=1):
#         '''Use pdemand (or a portion of it) to charge the battery.
#         Args:
#             - pdemand: power that we want to charge the battery with (in kW)
#             - tdelta: the time period during which pdemand is applied to the battery (in h)
#         Returns:
#             - pcharge: the power that is ultimately used on the battery
#             - premain: the remaining power, `pdemand - pcharge`
#             - sdcharge: the amount of self-discharge'''

#         assert pdemand >= 0

#         # self-discharge always happens
#         sdcharge = self._selfdischarge()

#         if pdemand == 0:
#             return 0, 0, sdcharge

#         # check if pdemand exceeds the max charging power
#         pcharge = min(self.maxcharge, pdemand)

#         # check if charging would exceed max state-of-charge
#         if self.etacharge * (pcharge * tdelta) + self.soc > self.maxsoc:
#             pcharge = (self.maxsoc - self.soc) / self.etacharge / tdelta

#         # charge the battery
#         self.soc = self.soc + self.etacharge * (pcharge * tdelta)
#         assert self.soc <= self.maxsoc

#         # 
#         premain = pdemand - pcharge
#         return pcharge, premain, sdcharge

#     def discharge(self, pdemand, tdelta=1):
#         '''Try to discharge pdemand of power from the battery.
#         Args:
#             - pdemand: the amount of power we need (in kW)
#             - tdelta: the time period while we discharge the battery (in h)
#         Returns:
#             - pdischarge: power used to discharge the battery (in kW)
#             - premain: remaining power, `pdemand - pdischarge`
#             - sdcharge: the amount of self-discharge
#         '''
#         assert pdemand >= 0

#         # self-discharge always happens
#         sdcharge = self._selfdischarge()

#         if pdemand == 0:
#             return 0, 0, sdcharge

#         pdischarge = min(pdemand / self.etadischarge, self.maxdischarge)

#         if self.soc - (pdischarge * tdelta) < self.minsoc:
#             pdischarge = (self.soc - self.minsoc) / tdelta
#         self.soc = self.soc - self.etadischarge * (pdischarge * tdelta)
#         self.soc = chop(self.soc)
#         assert self.soc >= self.minsoc

#         premain = chop(pdemand - pdischarge * self.etadischarge)
#         return pdischarge, premain, sdcharge

#     def power_to_max(self) -> float:
#         '''Returns the amount of power needed to charge up this battery to
#         the max.'''
#         return (self.maxsoc - self.soc) / self.etacharge

# class PeakShaveLiIonBattery(PeakShaveBattery):
#     def __init__(self) -> None:
#         super().__init__()

#     @classmethod
#     def _convert_config(cls):
#         super()._convert_config()
#         cls.selfdischarge = 1 - ((1 - cls.selfdischarge) ** (1/730))

# class PeakShaveFlywheel(PeakShaveBattery):
#     def __init__(self) -> None:
#         super().__init__()

# class PeakShaveSupercapacitor(PeakShaveBattery):
#     def __init__(self) -> None:
#         super().__init__()

# PeakShaveLiIonBattery._load_attributes(CONFIG['LiIonBattery'])
# PeakShaveFlywheel._load_attributes(CONFIG['Flywheel'])
# PeakShaveSupercapacitor._load_attributes(CONFIG['Supercapacitor'])

# class PeakShaveEnergyHub(EnergyHub):
#     def _init_batteries(self):
#         for _ in range(self.sucap_cnt):
#             self.storages.append(PeakShaveSupercapacitor())
#         for _ in range(self.flywh_cnt):
#             self.storages.append(PeakShaveFlywheel())
#         for _ in range(self.liion_cnt):
#             self.storages.append(PeakShaveLiIonBattery())
    
#     def charge(self, pdemand, tdelta=1):
#         '''Attempts to charge batteries in the storage in order.
#         Args:
#             - pdemand: demand load in kW, the amount of power we want to store
#             - tdelta: time duration for which charging power should be applied
#                       (in hour)
#         Returns:
#             - total amount charged (in kW)
#             - total charge lost to self-discharge (in kW)'''

#         total_charge = 0
#         total_selfdischarge = 0
#         for battery in self.storages:
#             pcharge, pdemand, sdcharge = battery.charge(pdemand, tdelta)
#             total_charge += pcharge
#             total_selfdischarge += sdcharge

#         return total_charge, total_selfdischarge

#     def discharge(self, pdemand, tdelta=1):
#         '''Attempts to discharge batteries in the storage in order.
#         Args:
#             - pdemand: demand load in kW, the amount of power we want to store
#             - tdelta: time duration for which charging power should be applied
#                       (in hour)
#         Returns:
#             - total amount charged (in kW)
#             - total charge lost to self-discharge (in kW)
#         '''
#         total_discharge = 0
#         total_selfdischarge = 0
#         for battery in self.storages:
#             pdischarge, pdemand, sdcharge = battery.discharge(pdemand, tdelta)
#             total_discharge += pdischarge
#             total_selfdischarge += sdcharge
#         return total_discharge, total_selfdischarge

#     def do_nothing(self):
#         total_selfdischarge = 0
#         for battery in self.storages:
#             _, _, sdcharge = battery.do_nothing()
#             total_selfdischarge += sdcharge
#         return 0, 0, total_selfdischarge

#     def get_soc(self):
#         '''Returns the total state-of-charge of all batteries (in kWh).'''
#         return sum(battery.get_soc() for battery in self.storages)
    
#     def get_maxsoc(self):
#         '''Returns the total maximum state-of-charge of all batteries (in kWh).'''
#         return sum([battery.get_maxsoc() for battery in self.storages])

#     def reset(self):
#         for battery in self.storages:
#             battery.reset()

#     def power_to_max(self):
#         '''Returns the amount of power necessary to charge the whole ehub to max.'''
#         power = 0
#         for battery in self.storages:
#             power += battery.power_to_max()
#         return power

#     def compute_reserve_time(self, pnet_list):
#         '''Given a list of power demands, computes how much time would we last on
#         our batteries only. We assume that the minimum SOC is zero.
#         Args:
#             - pnet_list: list of power demands
#         Returns:
#             - hours: how many hours would the batteries last'''
#         soc_list = self.save_soc()

#         hours = 0
#         for pnet in pnet_list:
#             self.discharge(pnet)
#             if self.get_soc() > 0:
#                 hours += 1
#             else:
#                 break

#         self.load_soc(soc_list)
#         return hours
    
#     def compute_full_reserve(self, pnet_list):
#         '''Given a list of power demands, computes, how long would we last if the
#         batteries were full.
#         Args:
#             - pnet_list: list of power demands
#         Returns:
#             - hours: '''
#         soc_list = self.save_soc()

#         for battery in self.storages:
#             battery.soc = battery.get_maxsoc()
#         hours = self.compute_reserve_time(pnet_list)

#         self.load_soc(soc_list)
#         return hours

#     def find_next_charge_time(self, price_list, treserve):
#         '''
#         Args:
#             - price_list: list of electricity prices
#             - treserve: amount of time the energyhub would last if it was full
#         '''
#         curr_price = price_list[0]
#         end = min(len(price_list), treserve + 1)
#         min_idx = np.argmin(price_list[:end])
#         return min_idx

#     def power_until(self, tstep, pnet_list):
#         pass
