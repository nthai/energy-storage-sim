from abc import ABC, abstractmethod
import os
import yaml

CONFIG = None
CONFFILE = 'batteries.yaml'
print(f'{os.path.basename(__file__)}: loading battery config from {CONFFILE}...')
with open(CONFFILE) as configfile:
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
        print(f'Loading config for {cls.__name__}...')
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
    
    def step(self, Pnet):
        '''Compute next state of charge. Steps 1 hour forward.
        params:
            - Pnet: net power (in kW) that is used to charge this battery
        returns:
            Pex export power that remains after charging (in kW). If
            negative, we need to pick up more energy.'''

        # self-discharge (always happens)
        self.soc = (1 - self.selfdischarge) * self.soc

        # if there is no net power, don't do anything
        if Pnet == 0:
            return Pnet

        Pex = 0
        # if we generated net power, try to charge
        if Pnet > 0:

            Pcharge = Pnet
            if Pnet > self.maxcharge: # too much charging
                Pcharge = self.maxcharge
                Pex += Pnet - Pcharge

            energy_plus = Pcharge * self.etacharge

            # if we would overcharge
            if self.soc + energy_plus > self.maxsoc:
                # charge until full
                self.soc = self.maxsoc
                # export remaining power
                Pex += (energy_plus - self.maxsoc - self.soc) / self.etacharge
            # if we would not overcharge
            else:
                self.soc += energy_plus

        # we need power, we will discharge
        else:
            if self.soc > self.minsoc: # there is charge in the storage

                # Pcharge = abs(Pnet)
                # if abs(Pnet) > self.maxdischarge: # too much discharge needed
                #     Pcharge = self.maxdischarge
                #     Pex += Pnet + Pcharge

                # Poffer is the total power we can offer
                Poffer = (self.soc - self.minsoc) * self.etadischarge
                Pdischarge = None

                # if we need more power than we can offer
                if abs(Pnet) > Poffer:
                    # discharge whole battery
                    Pdischarge = self.soc - self.minsoc

                # if we can satisfy the needs with discharging
                else:
                    # discharge enough for Pnet
                    Pdischarge = abs(Pnet) / self.etadischarge

                # check the if discharge exceeds the max discharge rate
                if Pdischarge > self.maxdischarge:
                    Pdischarge = self.maxdischarge
                # discharge
                self.soc -= Pdischarge
                Pex = Pnet + Pdischarge * self.etadischarge

            # no charge in the storage
            else:
                Pex += Pnet

        if abs(Pex) < 1e-8:
            Pex = 0
        return Pex

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

if __name__ == '__main__':
    a = LiIonBattery()
    print(a.soc)
    Pex = a.step(1000)
    print(Pex, a.soc)
