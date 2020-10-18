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
import os
import random
import time
import numpy as np


class RandomSelection:

    RETRIES = 5

    def __init__(self, problem_instance, time_budgets=None):
        self.name = "random"
        self.problem_instance = problem_instance
        if time_budgets is None:
            self.time_budgets = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
        else:
            self.time_budgets = time_budgets
        number_of_sets = len(problem_instance.available_test_cases)
        # get total execution time
        sol_vector = np.ones(number_of_sets)
        initial_sol = Solution(problem_instance, sol_vector)
        cost = initial_sol.cost
        self.time_budgets = list(map(lambda x: x * cost, self.time_budgets))
        self.population = []
        s = time.time()
        self.get_random_covers()
        self.search_duration = time.time() - s

    def draw_random_sol(self):
        index = random.randint(0, len(self.problem_instance.available_test_cases) - 1)
        cost = self.problem_instance.get_cost(index)
        return index, cost

    def get_sol_of_cost(self, budget):
        total = 0
        already = []
        re = 0
        while re < RandomSelection.RETRIES:
            index, set_cost = self.draw_random_sol()
            if index not in already and set_cost + total < budget:
                already.append(index)
                total += set_cost
                re = 0
            else:
                re += 1
        number_of_sets = len(self.problem_instance.available_test_cases)
        sol_vector = np.zeros(number_of_sets)
        initial_sol = Solution(self.problem_instance, sol_vector)
        for index in already:
            # initial_sol.set_vector[index] = 1
            initial_sol.add_set(index)
        return initial_sol

    def get_random_covers(self):
        random_covers = []
        for budget in self.time_budgets:
            random_covers.append(self.get_sol_of_cost(budget))
        self.population = random_covers

    def search(self):
        pass

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
        print("save random selection")
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
        save_as = "RESULTS" + os.sep + problem_name.replace("/", "_") + "_RANDOM_" + str(series_step) + "_" + str(repetition) + ".json"
        JsonDataManager.save_data_to(save_as, json_content)
