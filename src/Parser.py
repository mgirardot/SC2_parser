import pandas as pd
import numpy as np
import sys
import os

__author__ = "Michael Girardot"
__project__ = "StarCraft 2 replay parser"


class Parser:
    def __init__(self, data):
        self.result_DF = pd.DataFrame()
        self.data = data

        # remove parenthesis in action description
        self.data['action'] = self.data['action'].str.replace('[\(\)]', '')
        self.data['action'] = self.data['action'].str.replace('Mothership Core', 'Mothership_Core')
        self.p1 = self.data.loc[self.data['player'] == players[0]]
        self.p2 = self.data.loc[self.data['player'] == players[1]]



    def process(self):
        def list_trained_unit_types(df):
            '''
            :return: a list of unit types
            '''
            return list(set(df['action'].str.extract('\w+ (\w+)', expand=False)))

        def trained_units(df):
            """
            :param df: Dataframe
            :return: subset of the dataframe containing the Train keyword
            """
            return df[df['action'].str.contains('^Train') == True]

        def count_trained_units(df):
            """
            :param df: player dataframe
            :return: number of trained units
            """
            tu = trained_units(df)
            #remove Train word
            tu['action'].str.strip('Train ')
            #count the different types of units
            l = []
            for i, unit in enumerate(list_trained_unit_types(tu)):
                l.append([unit, len(tu[tu['action'].str.contains(unit)])])
            return l

        def append_list_to_resultDF(l, player=''):
            for line in l:
                self.result_DF[player + line[0].replace(' ','_')] = [line[1]]

        def variety_trained_units(df):
            tu = count_trained_units(df)
            return len(tu)

        def timings_1st_trained_unit_type(df,unit_type):
            tu = trained_units(df)
            return min(tu[tu['action'].str.contains(unit_type) == True].frames)

        def timings_trained_unit_type(df, unit_type):
            tu = trained_units(df)
            return tu[tu['action'].str.contains(unit_type) == True].frames

        def buildings(df):
            return df[df['action'].str.contains("Build")==True]

        def list_buildings_types(df):
            return list(set(df['action'].str.extract('\w+ (\w+ ?\w+)',expand=False)))

        def count_buildings_build(df):
            bu = buildings(df)
            l = []
            for i, building in enumerate(list_buildings_types(bu)):
                l.append([building, len(bu[bu['action'].str.contains(building)==True])])
            return l

        def variety_buildings(df):
            bu = count_buildings_build(df)
            return len(bu)

        def timings_1st_building_type(df, build_type):
            bu = buildings(df)
            return min(bu[bu['action'].str.contains(build_type)==True].frames)

        def timings_building_type(df, building):
            bu = buildings(df)
            return bu[bu['action'].str.contains(building)==True].frames

        def upgrades(df):
            result = df[df['action'].str.contains("Failed")==False]
            return result[result['action'].str.contains("Upgrade")==True]

        def list_upgrades(df):
            return list(set(upgrades(df)['action'].str.extract('\w+ (.*$)',expand=False)))

        def timings_upgrade_type(df, upgrade):
            up = upgrades(df)
            return up[up['action'].str.contains(upgrade)==True].frames

        def count_upgrades(df):
            l = []
            for i, upgrade in enumerate(list_upgrades(df)):
                # remove spamming == repeated keystrock
                tu = timings_upgrade_type(df, upgrade)
                timings = []
                for j,t in enumerate(tu):
                    if (j==0):
                        timings.append(t)
                    if (j > 0):
                        if (t > tu.iloc[j-1]+50):
                            timings.append(t)
                l.append([upgrade, len(timings)])
            return l

        def subset_move_screen(df):

            return df[df['action'].str.contains("Move screen")==True]

        def distance_from_opponent(df,opponent_df):
            sub_df = subset_move_screen(df)

            #extract x= and y=
            positions = sub_df['action'].str.extract('x=(?P<x>\d+\.\d+),y=(?P<y>\d+\.\d+)',expand=False)
            opponent_positions = opponent_df['action'].str.extract('x=(?P<x>\d+\.\d+),y=(?P<y>\d+\.\d+)', expand=False)[:1]

            #compute distances from opponent starting position
            distances = []
            for i,pos in positions.iterrows():
                distances.append(np.sqrt(np.square(float(pos[0]) - float(opponent_positions.x)) + np.square(float(pos[1]) - float(opponent_positions.y))))
            return distances

        def nb_scooting(player,opponent):
            scooting = [1 for x in distance_from_opponent(player,opponent) if x<17]
            return sum(scooting)

        def timing_1st_scooting(player,opponent):
            sub_player = subset_move_screen(player)
            i=0
            list_dist = []
            for distance in distance_from_opponent(sub_player,opponent):
                if distance<34:
                    list_dist.append(sub_player.iloc[i,0])
                i+=1
            if not list_dist:
                result = np.NaN
            else:
                result = list_dist[0]
            return result

        def min_distance_from_opponent(player,opponent):
            dist_list = distance_from_opponent(player,opponent)
            return pd.DataFrame(dist_list).rolling(2).mean().values[1:].min()

        def max_distance_from_opponent(player,opponent):
            dist_list = distance_from_opponent(player,opponent)
            return pd.DataFrame(dist_list).rolling(2).mean().values[1:].max()

        def mean_distance_from_opponent(player,opponent):
            dist_list = distance_from_opponent(player,opponent)
            return pd.DataFrame(dist_list).rolling(2).mean().values[1:].mean()

        def get_APM(df):
            return len(df) / ((float(df.frames.iloc[-1]) * 11.278) / 60000)

        def assigned_hotkeys(df):
            return len(df[df['action'].str.contains("Hotkey Assign")==True])

        def selected_hotkeys(df):
            return len(df[df['action'].str.contains("Hotkey Select")==True])

        def get_collecting_unit(df):
            return df[df['action'].str.contains("^Train")==True].action.str.split().str.get(1)[:1].max()

        def get_collecting_building(df):
            collecting_unit = get_collecting_unit(df)
            if collecting_unit:
                collecting_building = {
                "SCV": "Refinery",
                "Probe": "Assimilator",
                "Drone": "Extractor"
                }[collecting_unit]
                return collecting_building

        def get_unit_mineral_cost(unit):
            unit_cost = {
                'Archon' : 0 ,
                'Baneling' : 25 ,
                'Banshee' : 150 ,
                'Battlecruiser' : 400 ,
                'Brood' : 150 ,
                'Broodling' : 0 ,
                'Carrier' : 350 ,
                'Colossus' : 300 ,
                'Corruptor' : 150 ,
                'Dark' : 125 ,
                'Drone' : 50 ,
                'Ghost' : 200 ,
                'Hellbat' : 100 ,
                'Hellion' : 100 ,
                'High' : 50 ,
                'Hydralisk' : 100 ,
                'Immortal' : 250 ,
                'Infestor' : 100 ,
                'Larva' : 0 ,
                'Locust' : 0 ,
                'Lurker' : 50 ,
                'Marauder' : 100 ,
                'Marine' : 50 ,
                'Medivac' : 100 ,
                'Mothership' : 300 ,
                'Mothership_Core' : 100 ,
                'Mutalisk' : 100 ,
                'Nydus' : 100 ,
                'Observer' : 25 ,
                'Overlord' : 100 ,
                'Overseer' : 50 ,
                'Phoenix' : 150 ,
                'Probe' : 50 ,
                'Queen' : 150 ,
                'Ravager' : 25 ,
                'Raven' : 100 ,
                'Reaper' : 50 ,
                'Roach' : 75 ,
                'SCV' : 50 ,
                'Sentry' : 50 ,
                'Siege' : 150 ,
                'Stalker' : 125 ,
                'Swarm' : 200 ,
                'Thor' : 300 ,
                'Ultralisk' : 300 ,
                'Viking' : 150 ,
                'Viper' : 100 ,
                'Void' : 250 ,
                'Warp' : 200 ,
                'Widow' : 75 ,
                'Zealot' : 100 ,
                'Zergling' : 25 ,
                'an' : 0
            }[unit]
            return unit_cost

        def get_unit_gas_cost(unit):
            unit_cost = {
                'Archon' : 0 ,
                'Baneling' : 25 ,
                'Banshee' : 100 ,
                'Battlecruiser' : 300 ,
                'Brood' : 150 ,
                'Broodling' : 0 ,
                'Carrier' : 250 ,
                'Colossus' : 200 ,
                'Corruptor' : 100 ,
                'Dark' : 125 ,
                'Drone' : 0 ,
                'Ghost' : 100 ,
                'Hellbat' : 0 ,
                'Hellion' : 0 ,
                'High' : 150 ,
                'Hydralisk' : 50 ,
                'Immortal' : 100 ,
                'Infestor' : 150 ,
                'Larva' : 0 ,
                'Locust' : 0 ,
                'Lurker' : 100 ,
                'Marauder' : 25 ,
                'Marine' : 0 ,
                'Medivac' : 100 ,
                'Mothership' : 300 ,
                'Mothership_Core' : 100 ,
                'Mutalisk' : 100 ,
                'Nydus' : 100 ,
                'Observer' : 75 ,
                'Overlord' : 0 ,
                'Overseer' : 50 ,
                'Phoenix' : 100 ,
                'Probe' : 0 ,
                'Queen' : 0 ,
                'Ravager' : 75 ,
                'Raven' : 200 ,
                'Reaper' : 50 ,
                'Roach' : 25 ,
                'SCV' : 0 ,
                'Sentry' : 100 ,
                'Siege' : 125 ,
                'Stalker' : 50 ,
                'Swarm' : 100 ,
                'Thor' : 200 ,
                'Ultralisk' : 200 ,
                'Viking' : 75 ,
                'Viper' : 200 ,
                'Void' : 150 ,
                'Warp' : 0 ,
                'Widow' : 25 ,
                'Zealot' : 0 ,
                'Zergling' : 0 ,
                'an' : 0
            }[unit]
            return unit_cost

        def get_building_mineral_cost(building):
            building_cost = {
                'Armory' : 150 ,
                'Assimilator' : 75 ,
                'Auto Turret' : 0 ,
                'Baneling Nest' : 100 ,
                'Barracks' : 150 ,
                'Building Attack' : 0 ,
                'Bunker' : 100 ,
                'Command Center' : 400 ,
                'Creep Tumor' : 0 ,
                'Cybernetics Core' : 150 ,
                'Dark Shrine' : 150 ,
                'Engineering Bay' : 125 ,
                'Evolution Chamber' : 75 ,
                'Extractor' : 25 ,
                'Factory' : 150 ,
                'Fleet Beacon' : 300 ,
                'Forge' : 150 ,
                'Fusion Core' : 150 ,
                'Gateway' : 150 ,
                'Ghost Academy' : 150 ,
                'Hatchery' : 300 ,
                'Hive' : 200 ,
                'Hydralisk Den' : 100 ,
                'Infestation Pit' : 100 ,
                'Lair' : 150 ,
                'Missile Turret' : 100 ,
                'Nexus' : 400 ,
                'Nydus Network' : 150 ,
                'Nydus Worm' : 100 ,
                'Photon Cannon' : 150 ,
                'Point Defense' : 0 ,
                'Pylon' : 100 ,
                'Reactor Barracks' : 50 ,
                'Reactor Factory' : 50 ,
                'Reactor Starport' : 50 ,
                'Refinery' : 75 ,
                'Roach Warren' : 150 ,
                'Robotics Bay' : 200 ,
                'Robotics Facility' : 200 ,
                'Sensor Tower' : 125 ,
                'Spawning Pool' : 200 ,
                'Spine Crawler' : 100 ,
                'Spire' : 200 ,
                'Spore Crawler' : 75 ,
                'Stargate' : 150 ,
                'Starport' : 150 ,
                'Supply Depot' : 100 ,
                'Tech Lab' : 50 ,
                'Templar Archives' : 150 ,
                'Terran Building' : 0 ,
                'Twilight Council' : 150 ,
                'Ultralisk Cavern' : 150 ,
                'Warp Gate' : 0 ,
                'Lurker Den' : 150 ,
                'Greater Spire' : 100
            }[building]
            return building_cost

        def get_building_gas_cost(building):
            building_cost = {
                'Armory':100,
                'Assimilator':0,
                'Auto Turret':0,
                'Baneling Nest':50,
                'Barracks':0,
                'Building Attack':0,
                'Bunker':0,
                'Command Center':0,
                'Creep Tumor':0,
                'Cybernetics Core':0,
                'Dark Shrine':150,
                'Engineering Bay':0,
                'Evolution Chamber':0,
                'Extractor':0,
                'Factory':100,
                'Fleet Beacon':200,
                'Forge':0,
                'Fusion Core':150,
                'Gateway':0,
                'Ghost Academy':50,
                'Hatchery':0,
                'Hive':150,
                'Hydralisk Den':100,
                'Infestation Pit':100,
                'Lair':100,
                'Missile Turret':0,
                'Nexus':0,
                'Nydus Network':200,
                'Nydus Worm':100,
                'Photon Cannon':0,
                'Point Defense':0,
                'Pylon':0,
                'Reactor Barracks':50,
                'Reactor Factory':50,
                'Reactor Starport':50,
                'Refinery':0,
                'Roach Warren':0,
                'Robotics Bay':200,
                'Robotics Facility':100,
                'Sensor Tower':100,
                'Spawning Pool':0,
                'Spine Crawler':0,
                'Spire':200,
                'Spore Crawler':0,
                'Stargate':150,
                'Starport':100,
                'Supply Depot':0,
                'Tech Lab':25,
                'Templar Archives':200,
                'Terran Building':0,
                'Twilight Council':100,
                'Ultralisk Cavern':200,
                'Warp Gate':0,
                'Lurker Den':150,
                'Greater Spire':150
            }[building]
            return building_cost

        def get_upgrade_mineral_cost(upgrade):
            upgrade_cost = {
                'Lair Upgrade Hatchery': 150,
                'Orbital Command Upgrade Command Center': 150,
                'Planetary Fortress Upgrade Command Center': 150,
                'Protoss Air Armor 1': 150,
                'Protoss Air Armor 2': 225,
                'Protoss Air Armor 3': 300,
                'Protoss Air Weapons 1': 100,
                'Protoss Air Weapons 2': 175,
                'Protoss Air Weapons 3': 250,
                'Protoss Ground Armor 1': 100,
                'Protoss Ground Armor 2': 150,
                'Protoss Ground Armor 3': 200,
                'Protoss Ground Weapons 1': 100,
                'Protoss Ground Weapons 2': 150,
                'Protoss Ground Weapons 3': 200,
                'Protoss Shield 1': 150,
                'Protoss Shield 2': 225,
                'Protoss Shield 3': 300,
                'Terran Building Armor': 150,
                'Terran Hi-sec Auto Tracking': 100,
                'Terran Infantry Armor 1': 100,
                'Terran Infantry Armor 2': 175,
                'Terran Infantry Armor 3': 250,
                'Terran Infantry Weapons 1': 100,
                'Terran Infantry Weapons 2': 175,
                'Terran Infantry Weapons 3': 250,
                'Terran Neosteel Frame': 100,
                'Terran Ship Plating 1': 100,
                'Terran Ship Plating 2': 175,
                'Terran Ship Plating 3': 250,
                'Terran Ship Weapons 1': 100,
                'Terran Ship Weapons 2': 175,
                'Terran Ship Weapons 3': 250,
                'Terran Vehicle Plating 1': 100,
                'Terran Vehicle Plating 2': 175,
                'Terran Vehicle Plating 3': 250,
                'Terran Vehicle Weapons 1': 100,
                'Terran Vehicle Weapons 2': 175,
                'Terran Vehicle Weapons 3': 250,
                'Zerg Flyer Attacks 1': 100,
                'Zerg Flyer Attacks 2': 175,
                'Zerg Flyer Attacks 3': 250,
                'Zerg Flyer Carapace 1': 100,
                'Zerg Flyer Carapace 2': 175,
                'Zerg Flyer Carapace 3': 250,
                'Zerg Ground Carapace 1': 150,
                'Zerg Ground Carapace 2': 225,
                'Zerg Ground Carapace 3': 300,
                'Zerg Melee Attacks 1': 100,
                'Zerg Melee Attacks 2': 175,
                'Zerg Melee Attacks 3': 250,
                'Zerg Missile Attacks 1': 100,
                'Zerg Missile Attacks 2': 150,
                'Zerg Missile Attacks 3': 200,
                'to Orbital Command Command Center': 150,
                'to Planetary Fortress Command Center': 150,
                'to Warp Gate Gateway': 50
            }[upgrade]
            return upgrade_cost

        def get_upgrade_gas_cost(upgrade):
            upgrade_cost = {
                 'Lair Upgrade Hatchery': 100 ,
                 'Orbital Command Upgrade Command Center': 0 ,
                 'Planetary Fortress Upgrade Command Center': 150 ,
                 'Protoss Air Armor 1': 150 ,
                 'Protoss Air Armor 2': 225 ,
                 'Protoss Air Armor 3': 300 ,
                 'Protoss Air Weapons 1': 100 ,
                 'Protoss Air Weapons 2': 175 ,
                 'Protoss Air Weapons 3': 250 ,
                 'Protoss Ground Armor 1': 100 ,
                 'Protoss Ground Armor 2': 150 ,
                 'Protoss Ground Armor 3': 200 ,
                 'Protoss Ground Weapons 1': 100 ,
                 'Protoss Ground Weapons 2': 150 ,
                 'Protoss Ground Weapons 3': 200 ,
                 'Protoss Shield 1': 150 ,
                 'Protoss Shield 2': 225 ,
                 'Protoss Shield 3': 300 ,
                 'Terran Building Armor': 150 ,
                 'Terran Hi-sec Auto Tracking': 100 ,
                 'Terran Infantry Armor 1': 100 ,
                 'Terran Infantry Armor 2': 175 ,
                 'Terran Infantry Armor 3': 250 ,
                 'Terran Infantry Weapons 1': 100 ,
                 'Terran Infantry Weapons 2': 175 ,
                 'Terran Infantry Weapons 3': 250 ,
                 'Terran Neosteel Frame': 100 ,
                 'Terran Ship Plating 1': 100 ,
                 'Terran Ship Plating 2': 175 ,
                 'Terran Ship Plating 3': 250 ,
                 'Terran Ship Weapons 1': 100 ,
                 'Terran Ship Weapons 2': 175 ,
                 'Terran Ship Weapons 3': 250 ,
                 'Terran Vehicle Plating 1': 100 ,
                 'Terran Vehicle Plating 2': 175 ,
                 'Terran Vehicle Plating 3': 250 ,
                 'Terran Vehicle Weapons 1': 100 ,
                 'Terran Vehicle Weapons 2': 175 ,
                 'Terran Vehicle Weapons 3': 250 ,
                 'Zerg Flyer Attacks 1': 100 ,
                 'Zerg Flyer Attacks 2': 175 ,
                 'Zerg Flyer Attacks 3': 250 ,
                 'Zerg Flyer Carapace 1': 100 ,
                 'Zerg Flyer Carapace 2': 175 ,
                 'Zerg Flyer Carapace 3': 250 ,
                 'Zerg Ground Carapace 1': 150 ,
                 'Zerg Ground Carapace 2': 225 ,
                 'Zerg Ground Carapace 3': 300 ,
                 'Zerg Melee Attacks 1': 100 ,
                 'Zerg Melee Attacks 2': 175 ,
                 'Zerg Melee Attacks 3': 250 ,
                 'Zerg Missile Attacks 1': 100 ,
                 'Zerg Missile Attacks 2': 150 ,
                 'Zerg Missile Attacks 3': 200 ,
                 'to Orbital Command Command Center': 0 ,
                 'to Planetary Fortress Command Center': 150 ,
                 'to Warp Gate Gateway': 50
            }[upgrade]
            return upgrade_cost

        def collected_minerals(df):
            collecting_unit = get_collecting_unit(df)
            collecting_building = get_collecting_building(df)

            result = 0
            prev_time = 0
            for i,t in enumerate(timings_trained_unit_type(df, collecting_unit)):
                # starting with 6 collecting units
                units = 6+i
                timing = t - prev_time
                mined = 39 * units * timing * 11.278 / 60000
                result += mined
                prev_time = t
            for i,created in enumerate(timings_building_type(df, collecting_building)):
                timing = float(df.frames.iloc[-1]) - created
                # 4 collectors max on one gas instead of minerals
                notmined = 39 * 4 * timing * 11.278 / 60000
                result -= notmined
            return result

        def collected_gas(df):
            collecting_building = get_collecting_building(df)
            result = 0
            for i, created in enumerate(timings_building_type(df, collecting_building)):
                timing = float(df.frames.iloc[-1]) - created
                # 4 collecting units on gas instead of minerals
                mined = 39 * 4 * timing * 11.278 / 60000
                result += mined
            return result

        def minerals_spent(df):
            costs = []
            for u in count_trained_units(df):
                costs.append(get_unit_mineral_cost(u[0]) * u[1])
            for b in count_buildings_build(df):
                costs.append(get_building_mineral_cost(b[0]) * b[1])
            for up in count_upgrades(df):
                costs.append(get_upgrade_mineral_cost(up[0]) * b[1])
            return np.sum(costs)

        def gas_spent(df):
            costs = []
            for u in count_trained_units(df):
                costs.append(get_unit_gas_cost(u[0]) * u[1])
            for b in count_buildings_build(df):
                costs.append(get_building_gas_cost(b[0]) * b[1])
            for up in count_upgrades(df):
                costs.append(get_upgrade_gas_cost(up[0]) * b[1])
            return np.sum(costs)

        ##
        # Game stats
        ##
        self.result_DF['game_length'] = self.p1.frames[-1:] * 11.278 /1000
        self.result_DF['p1_win_game'] = np.sum(self.p2['action'].str.find('Leave game') == 0)
        self.result_DF.reset_index(drop=True, inplace=True)
        ##
        # Units
        ##
        append_list_to_resultDF(count_trained_units(self.p1),player='p1_')
        append_list_to_resultDF(count_trained_units(self.p2),player='p2_')
        self.result_DF['p1_unit_types'] = variety_trained_units(self.p1)
        self.result_DF['p2_unit_types'] = variety_trained_units(self.p2)
        for unit in list_trained_unit_types(trained_units(self.p1)):
            self.result_DF['p1_1st_' + unit] = [timings_1st_trained_unit_type(self.p1, unit)]
        for unit in list_trained_unit_types(trained_units(self.p2)):
            self.result_DF['p2_1st_' + unit] = [timings_1st_trained_unit_type(self.p2, unit)]
        ##
        # Buildings
        ##
        append_list_to_resultDF(count_buildings_build(self.p1), player='p1_')
        append_list_to_resultDF(count_buildings_build(self.p2), player='p2_')
        self.result_DF['p1_building_types'] = variety_buildings(self.p1)
        self.result_DF['p2_building_types'] = variety_buildings(self.p2)
        for building in list_buildings_types(buildings(self.p1)):
            self.result_DF['p1_1st_' + building.replace(' ','_')] = [timings_1st_building_type(self.p1, building)]
        for building in list_buildings_types(buildings(self.p2)):
            self.result_DF['p2_1st_' + building.replace(' ','_')] = [timings_1st_building_type(self.p2, building)]
        ##
        # Upgrades
        ##
        append_list_to_resultDF(count_upgrades(self.p1), player='p1_')
        append_list_to_resultDF(count_upgrades(self.p2), player='p2_')
        for upgrade in list_upgrades(upgrades(self.p1)):
            self.result_DF['p1_1st_' + upgrade.replace(' ','_')] = [timings_upgrade_type(self.p1, upgrade).iloc[0]]
        for upgrade in list_upgrades(upgrades(self.p2)):
            self.result_DF['p2_1st_' + upgrade.replace(' ', '_')] = [timings_upgrade_type(self.p2, upgrade).iloc[0]]
        ##
        # Scooting
        ##
        self.result_DF['p1_nb_scooting'] = nb_scooting(self.p1,self.p2)
        self.result_DF['p2_nb_scooting'] = nb_scooting(self.p2,self.p1)
        self.result_DF['p1_timing_1st_scooting'] = timing_1st_scooting(self.p1,self.p2)
        self.result_DF['p2_timing_1st_scooting'] = timing_1st_scooting(self.p2,self.p1)
        self.result_DF['p1_min_distance_from_opponent'] = min_distance_from_opponent(self.p1,self.p2)
        self.result_DF['p2_min_distance_from_opponent'] = min_distance_from_opponent(self.p2, self.p1)
        self.result_DF['p1_max_distance_from_opponent'] = max_distance_from_opponent(self.p1,self.p2)
        self.result_DF['p2_max__distance_from_opponent'] = max_distance_from_opponent(self.p2, self.p1)
        self.result_DF['p1_mean_distance_from_opponent'] = mean_distance_from_opponent(self.p1, self.p2)
        self.result_DF['p2_mean_distance_from_opponent'] = mean_distance_from_opponent(self.p2, self.p1)
        ##
        # Keystrokes
        ##
        self.result_DF['p1_APM'] = get_APM(self.p1)
        self.result_DF['p2_APM'] = get_APM(self.p2)
        self.result_DF['p1_APM_wo_select'] = get_APM(self.p1[self.p1['action'].str.contains("Move screen | Select")==False])
        self.result_DF['p2_APM_wo_select'] = get_APM(self.p2[self.p2['action'].str.contains("Move screen | Select") == False])
        self.result_DF['p1_assigned_hotkeys'] = assigned_hotkeys(self.p1)
        self.result_DF['p2_assigned_hotkeys'] = assigned_hotkeys(self.p2)
        self.result_DF['p1_selected_hotkeys'] = selected_hotkeys(self.p1)
        self.result_DF['p2_selected_hotkeys'] = selected_hotkeys(self.p2)
        ##
        # Ressources mining
        ##
        self.result_DF['p1_collected_minerals'] = collected_minerals(self.p1)
        self.result_DF['p2_collected_minerals'] = collected_minerals(self.p2)
        self.result_DF['p1_collected_gas'] = collected_gas(self.p1)
        self.result_DF['p2_collected_gas'] = collected_gas(self.p2)
        self.result_DF['p1_spent_minerals'] = minerals_spent(self.p1)
        self.result_DF['p2_spent_minerals'] = minerals_spent(self.p2)
        self.result_DF['p1_spent_gas'] = gas_spent(self.p1)
        self.result_DF['p2_spent_gas'] = gas_spent(self.p2)


if __name__ == '__main__':
    e = 0
    final_DF = pd.DataFrame()
    directory = sys.argv[1]
    target = sys.argv[2]
    for fileName in os.listdir(directory):
        print ("Processing %s" % fileName)
        inputFile = os.path.join(directory, fileName)
        data = pd.read_csv(inputFile,
                                skiprows=2,
                                delimiter='\t',
                                #engine='python',
                                header=None,
                                names=["frames", "player", "action"],
                                error_bad_lines=False)
        players = list(set(data.iloc[:, 1]))
        # print ("Number of players: %d" % len(players))
        # df = Parser(data)
        # print df.data.head()
        # df.process()
        # print df.result_DF.head()

        if len(players)==2:
            print ("process file...")
            try:
                df = Parser(data)
                #print df.data.head()
                df.process()
                #print df.result_DF.head()
                final_DF = pd.concat([final_DF,df.result_DF],ignore_index=True)
                print ("Appending to final_DF")
                print ("Length final_DF: %d" % len(final_DF))
                final_DF.to_csv(target, index=False)
                # if not os.path.isfile(target):
                #     df.result_DF.to_csv(target, index=False)
                #     print ("Creating file %s " % target)
                # else:
                #     df.result_DF.to_csv(target, index=False, header=False, mode='a')
                #     print ("Appending to %s" % target)
            except:
                e += 1
                print ("Error in %s" % fileName)
                print ("Number of error files: %d" % e)
                pass
        else:
            print ("Not a 1v1 game...")
