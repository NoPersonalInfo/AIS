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


class SEMO:

    def __init__(self, opt_problem, iterations, border=200):
        self.opt_problem = opt_problem
        self.iterations = iterations
        initial_sol = Solution(opt_problem)
        self.population = AISPopulation(initial_sol, border)
        self.iter = 0
        self.mut_prob = 1.0 / len(opt_problem.failed_once)

    def mutate(self, solution):
        mutated = copy.deepcopy(solution.vals)
        for i in range(0, len(mutated)):
            if random.random() < self.mut_prob:
                mutated[i] = 1 if mutated[i] == 0 else 0
        return Solution(self.opt_problem, mutated)

    def mutate_and_insert(self):
        size = 0
        for key in self.population.table.keys():
            size += len(self.population.table[key]["sols"])
        index = random.randint(0, size - 1)
        counter = 0
        to_mutate = None
        for key in self.population.table.keys():
            if counter + len(self.population.table[key]["sols"]) > index:
                to_mutate = self.population.table[key]["sols"][index - counter]
            else:
                counter += len(self.population.table[key]["sols"])
        mutated = self.mutate(to_mutate)
        return self.population.try_insert(mutated)

    def iteration(self):
        print("SEMO: performed iteration " + str(self.iter) + " of " + str(self.iterations))
        pareto_changed = self.mutate_and_insert()
        self.population.clean()
        self.iter = self.iter + 1
        return pareto_changed

    def search(self):
        found = -1
        s = time.time()
        for i in range(0, self.iterations):
            pareto_changed = self.iteration()
            if pareto_changed:
                found = i
            if has_converged(found, self.iter, time.time() - s):
                self.search_duration = time.time() - s
                break
        self.search_duration = time.time() - s

    def get_solution_for_budget(self, time_budget):
        return self.population.find_sol(time_budget)

    def __get_total_duration(self):
        sol = Solution(self.opt_problem, list(map(lambda x: 1, Solution(self.opt_problem).vals)))
        return sol.cost

    def save(self, problem_name, budgets, series_step, repetition):
        print("save SEMO population")
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
        save_as = "RESULTS" + os.sep + problem_name.replace("/", "_") + "_SEMO_" + str(series_step) + "_" + str(repetition) + ".json"
        JsonDataManager.save_data_to(save_as, json_content)
