import random


class AISPopulation:

    def __init__(self, initial_sol, border):
        self.table = {}
        initial = initial_sol.fitness
        self.table[initial] = {}
        self.table[initial]["sols"] = [initial_sol]
        self.table[initial]["cost"] = initial_sol.cost
        self.max_cost = initial_sol.cost
        self.border = border

    def try_insert(self, sol):
        cost = sol.cost
        try:
            if self.table[sol.fitness]["cost"] > cost:
                self.table[sol.fitness]["sols"] = [sol]
                self.table[sol.fitness]["cost"] = sol.cost
                return True
            elif self.table[sol.fitness]["cost"] == cost:
                self.table[sol.fitness]["sols"].append(sol)
                if len(self.table[sol.fitness]["sols"]) > self.border:
                    to_rem = random.randint(0, len(self.table[sol.fitness]["sols"]) - 1)
                    del self.table[sol.fitness]["sols"][to_rem]
                return True
            return False
        except KeyError:
            self.table[sol.fitness] = {}
            self.table[sol.fitness]["cost"] = sol.cost
            self.table[sol.fitness]["sols"] = [sol]
            return True

    def clean(self):
        '''
        cleans up the table after (not threadsafe should be run sequentially)
        '''
        pass
        '''
        keys = list(map(lambda x: float(x), self.table.keys()))
        keys = sorted(keys, reverse=True)
        if len(keys) > 1:
            last = keys[1]
            for i in keys:
                try:
                    if self.table[last]["cost"] <= self.table[i]["cost"]:
                        del self.table[i]
                    else:
                        last = i
                except KeyError:
                    pass
        '''

    def find_sol(self, time_budget):
        '''
        Searches for the solution with highest coverage that is still within the time budget.

        :param time_budget: available time_budget

        :return : A solution if one is found, otherwise None
        '''
        keys = list(map(lambda x: float(x), self.table.keys()))
        for i in reversed(sorted(keys)):
            try:
                if self.table[i]["cost"] <= time_budget:
                    return self.table[i]["sols"][0]
            except KeyError:
                pass
