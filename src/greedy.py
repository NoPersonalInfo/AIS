"""
COPYRIGHT © BSH HOME APPLIANCES GROUP  2020

ALLE RECHTE VORBEHALTEN. ALL RIGHTS RESERVED.

The reproduction, transmission or use of this document or its contents is not permitted without express
written authority. Offenders will be liable for damages. All rights, including rights created by  patent
grant or registration of a utility model or design, are reserved.
"""
try:
    from src.opt import has_converged, Solution
    from src.ais_population import AISPopulation
    from src.json_reader import JsonDataManager
except Exception as _:
    from opt import has_converged, Solution
    from ais_population import AISPopulation
    from json_reader import JsonDataManager
import copy
import os
import random
import time
import numpy as np


class Greedy:

    COVERAGE = 0
    FAULT = 1

    def __init__(self, problem_instance, mode):
        self.name = "GREEDY_"
        if mode == Greedy.COVERAGE:
            self.name += "COVERAGE"
        elif mode == Greedy.FAULT:
            self.name += "FAULT"
        self.mode = mode
        self.problem_instance = problem_instance
        self.population = [Solution(problem_instance)]

    def get_next_best(self, curr_solution):
        if self.mode == Greedy.COVERAGE:
            return self.problem_instance.get_greedy_next_coverage(curr_solution)
        elif self.mode == Greedy.FAULT:
            return self.problem_instance.get_greedy_next_fault(curr_solution)

    def search(self):
        s = time.time()
        index = self.get_next_best(self.population[0])
        curr_sol = self.population[0]
        count = 0
        while index is not None:
            curr_sol.add_set(index)
            self.population.append(curr_sol)
            curr_sol = Solution(curr_sol.opt_prob, copy.deepcopy(curr_sol.vals))
            index = self.get_next_best(curr_sol)
            count += 1
        self.search_duration = time.time() - s

    def get_solution_for_budget(self, time_budget):
        fitness = 0
        best = None
        for ele in self.population:
            if ele.fitness > fitness and ele.cost <= time_budget:
                best = ele
                fitness = ele.fitness
        return best

    def __get_total_duration(self):
        sol = Solution(self.problem_instance, list(map(lambda x: 1, Solution(self.problem_instance).vals)))
        return sol.cost

    def save(self, problem_name, budgets, series_step, repetition):
        print("save greedy selection")
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
            entry["percentage_found_errors"] = self.problem_instance.get_percentage_of_found_errors(sol)
            entry["percentage_found_failed_tests"] = self.problem_instance.get_percentage_of_failed_tests(sol)
            entry["coverage"] = sol.coverage
            entry["avg_fail_prob"] = sol.avg_fail_prob
            entry["number_of_tests"] = sum(sol.vals) / len(sol.vals)
            to_save.append(entry)
        json_content = {}
        json_content["search_duration"] = self.search_duration
        json_content["results"] = to_save
        json_content["cost"] = Solution(self.problem_instance, "full").cost
        save_as = "RESULTS" + os.sep + problem_name.replace("/", "_") + "_" + self.name + "_" + str(series_step) + "_" + str(repetition) + ".json"
        JsonDataManager.save_data_to(save_as, json_content)
