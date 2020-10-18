try:
    from src.opt import has_converged, Solution
    from src.ais_population import AISPopulation
    from src.json_reader import JsonDataManager
    from src.greedy import Greedy
except Exception as _:
    from opt import has_converged, Solution
    from ais_population import AISPopulation
    from json_reader import JsonDataManager
    from greedy import Greedy
import copy
import os
import random
import time
import numpy as np


class RandInitializer:

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

    def draw_random_sol(self):
        index = random.randint(0, len(self.problem_instance.available_test_cases) - 1)
        cost = self.problem_instance.get_cost(index)
        return index, cost

    def get_sol_of_cost(self, budget):
        total = 0
        already = []
        re = 0
        while re < RandInitializer.RETRIES:
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
        return random_covers


class AIS:

    def __init__(self, opt_problem, iterations, border=200, with_init=True):
        self.opt_problem = opt_problem
        self.iterations = iterations
        initial_sol = Solution(opt_problem)
        self.population = AISPopulation(initial_sol, border)
        self.with_init = with_init
        if with_init:
            other_sols = RandInitializer(opt_problem).get_random_covers()
            for sol in other_sols:
                self.population.try_insert(sol)
            greedy = Greedy(opt_problem, 1)
            greedy.search()
            for sol in greedy.population:
                self.population.try_insert(sol)
        self.iter = 0
        self.mut_prob = 1.0 / len(opt_problem.failed_once)

    def mutate(self, solution):
        mutated = copy.deepcopy(solution.vals)
        for i in range(0, len(mutated)):
            if random.random() < self.mut_prob:
                mutated[i] = 1 if mutated[i] == 0 else 0
        return Solution(self.opt_problem, mutated)

    def mutate_and_insert(self):
        pareto_changed = False
        mutated = []
        for key in self.population.table.keys():
            chunk = self.population.table[key]["sols"]
            mutated.append(list(map(lambda x: self.mutate(x), chunk)))
        for mutations in mutated:
            for mutated in mutations:
                pareto_changed = pareto_changed or self.population.try_insert(mutated)
        return pareto_changed

    def iteration(self):
        print("AIS: performed iteration " + str(self.iter) + " of " + str(self.iterations))
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
        print("save AIS population")
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
        if self.with_init:
            save_as = "RESULTS" + os.sep + problem_name.replace("/", "_") + "_ais_directed_" + str(series_step) + "_" + str(repetition) + ".json"
        else:
            save_as = "RESULTS" + os.sep + problem_name.replace("/", "_") + "_ais_undirected_" + str(
                series_step) + "_" + str(repetition) + ".json"
        JsonDataManager.save_data_to(save_as, json_content)
