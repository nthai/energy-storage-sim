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
        print('\n'.join([f'\t{k}: {v}' for k, v in config.items()]))

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

        if Pnet == 0: # no power, don't do anything
            return Pnet

        Pex = 0

        if Pnet > 0: # we generated more power, we will charge

            Pcharge = Pnet
            if Pnet > self.maxcharge: # too much charging
                Pcharge = self.maxcharge
                Pex += Pnet - Pcharge

            energy_plus = Pcharge * self.etacharge
            discharge_minus = self.selfdischarge * self.soc

            # if we would overcharge
            if self.soc + energy_plus - discharge_minus > self.capacity:
                used = self.capacity - (self.soc - discharge_minus)
                self.soc = self.capacity # only charge until full
                Pex += (energy_plus - used) / self.etacharge
            else: # we would not overcharge
                # just charge
                self.soc = self.soc + energy_plus - discharge_minus
            
        else: # we need power, we will discharge
            if self.soc > self.minsoc: # there is charge in the storage
                # self-discharge
                selfdisc = self.soc * self.selfdischarge
                self.soc -= selfdisc

                Pcharge = abs(Pnet)
                if abs(Pnet) > self.maxdischarge: # too much discharge needed
                    Pcharge = self.maxdischarge
                    Pex += Pnet + Pcharge

                to_discharge = Pcharge * self.etadischarge
                # too much discharge needed
                if self.soc - to_discharge < self.minsoc:
                    need = to_discharge - (self.soc - self.minsoc)
                    self.soc = self.minsoc
                    Pex -= need / self.etadischarge
                    
                else: # enough energy
                    self.soc -= to_discharge

            else: # no charge in the storage
                Pex += Pnet

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
    b = Supercapacitor()
    c = Flywheel()
