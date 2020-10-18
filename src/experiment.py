from copy import deepcopy
try:
    from src.opt import BSHOptProblem
    from src.ais import AIS
    from src.random_selection import RandomSelection
    from src.greedy import Greedy
    from src.semo import SEMO
    from src.NSGA import NSGA
except Exception as e:
    from opt import BSHOptProblem
    from ais import AIS
    from random_selection import RandomSelection
    from greedy import Greedy
    from semo import SEMO
    from NSGA import NSGA
import multiprocessing


class Experiment:

    TIME_BUDGETS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
    REPETITIONS = 10
    PROCESSES = 10
    ALGORITHMS = [
        lambda sci: RandomSelection(sci, Experiment.TIME_BUDGETS),
        lambda sci: NSGA(sci, 100, 0.9, 5000),
        lambda sci: Greedy(sci, 0),
        lambda sci: Greedy(sci, 1),
        lambda sci: SEMO(sci, 2000, 200),
        lambda sci: AIS(sci, 5000, 200),
        lambda sci: AIS(sci, 5000, 200, False)
    ]

    TEST_DATASETS = ["dishwasher", "oven1", "oven2"]


    def __init__(self):
        self.opt_problems = {}
        for dataset in Experiment.TEST_DATASETS:
            opt = BSHOptProblem(dataset)
            self.opt_problems[dataset] = opt

    def perform_repetition(self, iter):
        for key in self.opt_problems:
            prob = deepcopy(self.opt_problems[key])
            for i in range(prob.counter, prob.max_series):
                for algo in Experiment.ALGORITHMS:
                    alg_instance = algo(prob)
                    alg_instance.search()
                    alg_instance.save(key, Experiment.TIME_BUDGETS, i, iter)
                prob.step_forward()
            del prob

    def start_experiments(self, parallel):
        if parallel:
            p = multiprocessing.Pool(Experiment.PROCESSES)
            avg_res = p.map(self.perform_repetition, range(Experiment.REPETITIONS))
        else:
            for i in range(0, Experiment.REPETITIONS):
                self.perform_repetition(i)


exp = Experiment()
exp.start_experiments(True)
