"""
COPYRIGHT © BSH HOME APPLIANCES GROUP  2020

ALLE RECHTE VORBEHALTEN. ALL RIGHTS RESERVED.

The reproduction, transmission or use of this document or its contents is not permitted without express
written authority. Offenders will be liable for damages. All rights, including rights created by  patent
grant or registration of a utility model or design, are reserved.
"""
import copy
import os
import random
from sys import maxsize
import time
import traceback
try:
    from src.opt import has_converged, Solution
    from src.ais_population import AISPopulation
    from src.json_reader import JsonDataManager
    from src.greedy import Greedy
    from src.ais import RandInitializer
except Exception as _:
    from opt import has_converged, Solution
    from ais_population import AISPopulation
    from json_reader import JsonDataManager
    from greedy import Greedy
    from ais import RandInitializer


class NSGA:

    def __init__(self, opt_problem, max_size, hux_prob, no_iter):
        self.opt_problem = opt_problem
        self.population = RandInitializer(opt_problem).get_random_covers()
        self.max_size = max_size
        self.hux_prob = hux_prob
        self.no_iter = no_iter
        self.iteration = 0
        self.last_pareto = []

    def __fast_non_dominating_sort(self):
        dom_meta_info = {}
        fronts = {0: []}
        for member in self.population:
            dom_meta_info[member] = {}
            dom_meta_info[member]["dominates"] = []
            dom_meta_info[member]["domination_count"] = 0
            dom_meta_info[member]["rank"] = 0
            for other_member in self.population:
                if member.dominates(other_member):
                    dom_meta_info[member]["dominates"].append(other_member)
                elif other_member.dominates(member):
                    dom_meta_info[member]["domination_count"] += 1
            if dom_meta_info[member]["domination_count"] == 0:
                dom_meta_info[member]["rank"] = 0
                fronts[0].append(member)
        i = 0
        while len(fronts[i]) != 0:
            fronts[i + 1] = []
            for member in fronts[i]:
                for other_member in dom_meta_info[member]["dominates"]:
                    dom_meta_info[other_member]["domination_count"] -= 1
                    if dom_meta_info[other_member]["domination_count"] == 0:
                        dom_meta_info[other_member]["rank"] = i + 1
                        fronts[i + 1].append(other_member)
            i += 1
        if i - 1 > 0:
            del fronts[i - 1]
        assert fronts[0] is not None
        assert len(fronts[0]) > 0
        return fronts, dom_meta_info

    def __get_min_max_objectives(self):
        objectives = list(map(lambda x: x.get_objectives(), self.population))
        minima = []
        maxima = []
        for objective_index in range(0, len(objectives[0])):
            objective = list(map(lambda x: x[objective_index], objectives))
            minima.append(min(objective))
            maxima.append(max(objective))
        return minima, maxima

    def __crowding_dist(self, sol_set, minima, maxima):
        size = len(sol_set)
        crowd_dists = {}
        for member in sol_set:
            crowd_dists[member] = 0
        for objective_index in range(0, len(sol_set[0].get_objectives())):
            discount = maxima[objective_index] - minima[objective_index]
            sorted_for_index = sorted(sol_set, key=lambda x: (x.objectives[objective_index], random.random()))
            crowd_dists[sorted_for_index[0]] = maxsize
            crowd_dists[sorted_for_index[-1]] = maxsize
            for i in range(1, size - 1):
                crowd_dists[sorted_for_index[i]] += (sorted_for_index[i + 1].objectives[objective_index] - sorted_for_index[i - 1].objectives[objective_index]) / discount
        return crowd_dists

    def __crowded_comparison(self, sol_a, sol_b, dom_meta_info, crowdists):
        if dom_meta_info[sol_a]["rank"] > dom_meta_info[sol_b]["rank"]:
            return True
        if dom_meta_info[sol_a]["rank"] < dom_meta_info[sol_b]["rank"]:
            return False
        if crowdists[sol_a] < crowdists[sol_b]:
            return True
        return False

    def __selection(self):
        # binary tounament selection
        pop_size = len(self.population)
        selected = list(map(lambda x: self.population[x], [random.randint(0, pop_size - 1), random.randint(0, pop_size - 1)]))
        if selected[0].dominates(selected[1]):
            return selected[0]
        return selected[1]

    def __crossover(self, parent1, parent2):
        vals1 = copy.deepcopy(parent1.vals)
        vals2 = copy.deepcopy(parent2.vals)
        for i in range(0, len(vals1)):
            if vals1[i] != vals2[i] and random.random() <= self.hux_prob:
                temp = vals1[i]
                vals1[i] = vals2[i]
                vals2[i] = temp
        return Solution(self.opt_problem, vals1), Solution(self.opt_problem, vals2)

    def __mutation(self, child):
        vals = copy.deepcopy(child.vals)
        mut_prob = 1.0 / len(vals)
        for i in range(0, len(vals)):
            if random.random() < mut_prob:
                vals[i] = 1 if vals[i] == 0 else 0
        return Solution(self.opt_problem, vals)

    def __create_offspring_population(self):
        next_gen = []
        for i in range(0, int(self.max_size / 2)):
            parent1 = self.__selection()
            parent2 = self.__selection()
            child1, child2 = self.__crossover(parent1, parent2)
            child1 = self.__mutation(child1)
            child2 = self.__mutation(child2)
            next_gen.append(child1)
            next_gen.append(child2)
        return next_gen

    def __iteration(self):
        self.iteration += 1
        offspring = self.__create_offspring_population()
        self.population.extend(offspring)
        fronts, dom_meta_info = self.__fast_non_dominating_sort()
        minima, maxima = self.__get_min_max_objectives()
        self.population = fronts[0][:self.max_size]
        front_index = 1
        crowd_dists = []
        try:
            while len(self.population) + len(fronts[front_index]) < self.max_size:
                #assert len(fronts[front_index]) > 0
                crowd_dists.append(self.__crowding_dist(fronts[front_index], minima, maxima))
                self.population.extend(fronts[front_index])
                front_index += 1
        except Exception as _:
            front_index -= 1
            if front_index < 0:
                front_index = 0
        try:
            if len(self.population) + len(fronts[front_index]) >= self.max_size:
                if front_index < len(fronts):
                    crowd_dists.append(self.__crowding_dist(fronts[front_index], minima, maxima))
                crowd_dist_list = crowd_dists[front_index]
                while len(self.population) < self.max_size:
                    best = None
                    for key in crowd_dist_list.keys():
                        if best is None:
                            best = key
                        if self.__crowded_comparison(best, key, dom_meta_info, crowd_dist_list):
                            best = key
                    assert best is not None
                    self.population.append(best)
                if self.last_pareto is None:
                    self.last_pareto = fronts[0]
                    return True
                if len(self.last_pareto) != len(fronts[0]):
                    self.last_pareto = fronts[0]
                    return True
        except Exception as e:
            traceback.print_exc()
            print(e)
        only_last = list(filter(lambda x: x not in fronts[0], self.last_pareto))
        only_current = list(filter(lambda x: x not in self.last_pareto, fronts[0]))
        if len(only_last) != 0 or len(only_current) != 0:
            self.last_pareto = fronts[0]
            return False
        self.last_pareto = fronts[0]
        assert len(self.population) > 0
        return True

    def __get_total_duration(self):
        sol = Solution(self.opt_problem, list(map(lambda x: 1, Solution(self.opt_problem).vals)))
        return sol.cost

    def get_solution_for_budget(self, budget):
        try:
            in_range = list(filter(lambda x: x.cost <= budget, self.population))
            max_fit = max(list(map(lambda x: x.fitness, in_range)))
            return list(filter(lambda x: x.fitness == max_fit, in_range))[0]
        except Exception as _:
            return None

    def search(self):
        found = -1
        s = time.time()
        for i in range(0, self.no_iter):
            if i % 10 == 0:
                print("performed iteration " + str(i) + " of " + str(self.no_iter))
            pareto_changed = self.__iteration()
            if pareto_changed:
                found = i
            if has_converged(found, self.iteration, time.time() - s):
                self.search_duration = time.time() - s
                break
        self.search_duration = time.time() - s

    def save(self, problem_name, budgets, series_step, repetition):
        print("save NSGA population")
        total_cost = self.__get_total_duration()
        retrieved = []
        for relative_budget in budgets:
            budget = total_cost * relative_budget
            solution = self.get_solution_for_budget(budget)
            if solution is not None:
                retrieved.append(solution)
        to_save = []
        for sol in retrieved:
            entry = {}
            entry["cost"] = sol.cost
            entry["fitness"] = sol.fitness
            entry["percentage_found_errors"] = self.opt_problem.get_percentage_of_found_errors(sol)
            entry["percentage_found_failed_tests"] = self.opt_problem.get_percentage_of_failed_tests(sol)
            entry["coverage"] = sol.coverage
            entry["avg_fail_prob"] = sol.avg_fail_prob
            entry["number_of_tests"] = sum(sol.vals) / len(sol.vals)
            to_save.append(entry)
        json_content = {}
        json_content["search_duration"] = self.search_duration
        json_content["results"] = to_save
        json_content["cost"] = Solution(self.opt_problem, "full").cost
        save_as = "RESULTS" + os.sep + problem_name.replace("/", "_") + "_nsga_" + str(series_step) + "_" + str(repetition) + ".json"
        JsonDataManager.save_data_to(save_as, json_content)
