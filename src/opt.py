try:
    from src.json_reader import JsonDataManager
except Exception as e:
    from json_reader import JsonDataManager
import numpy as np
import os


class Constants:
    PASS = 1
    FAIL = 0


class CorrelationEntry:

    def __init__(self, test_name):
        self.test_name = test_name
        self.runs = 0
        self.total_fails = 0
        self.common_failed = {}
        self.common_run = {}
        self.total_run = 0

    def get_name(self):
        return self.test_name

    def update(self, all, own_entry):
        self.runs += 1
        if own_entry[1] == Constants.FAIL:
            self.total_fails += 1
        for ele in all:
            if int(ele[1]) == Constants.FAIL and int(own_entry[1]) == Constants.FAIL:
                try:
                    self.common_failed[ele[0]] += 1
                except Exception:
                    self.common_failed[ele[0]] = 1
            try:
                # print("ho")
                self.common_run[ele[0]] += 1
            except Exception:
                self.common_run[ele[0]] = 1
        self.total_run += float(own_entry[-1])

    def get_avg_duration(self):
        return self.total_run / self.runs

    def get_avg_fail(self):
        return self.total_fails / self.runs

    def get_approx_prob(self, other):
        '''
        :param other: name of the other test case
        :return: approximation of P(other fails | self fails)
        '''
        try:
            print((self.common_failed[other]) / self.common_run[other])
            return (self.common_failed[other]) / self.common_run[other]
        except Exception:
            return 0.0

    def get_trust(self, other):
        try:
            if self.common_failed[other] > 0:
                joint_prob = (self.common_failed[other]) / self.common_run[other]
                return 1.0 / joint_prob
            else:
                return 0.0
        except Exception:
            return 0.0

    def get_weighted_trust(self, other):
        return self.get_trust(other) * self.get_avg_fail()

    def get_approx_cond_prob(self, other):
        joint_prob = 0
        try:
            if self.common_failed[other.test_name] > 0:
                joint_prob = (self.common_failed[other.test_name]) / self.common_run[other.test_name]
        except Exception as e:
            return 0
        single_prob = self.get_avg_fail()
        if single_prob == 0:
            return 0
        return joint_prob / single_prob


class CorrelationTable:

    def __init__(self):
        self.table = []

    def __has_entry(self, name):
        count = len(list(filter(lambda x: x.get_name() == name, self.table)))
        assert count < 2
        return count > 0

    def find_entry(self, name):
        hits = list(filter(lambda x: x.get_name() == name, self.table))
        assert len(hits) < 2
        if len(hits) == 0:
            return None
        else:
            return hits[0]

    def has_failed_once(self, tc):
        try:
            entry = self.find_entry(tc)
            return entry.total_fails > 0
        except Exception as e:
            return False

    def update_table(self, results):
        '''

        :param results: list of lists. Each element is a list containing three entries as follows: 0) name of the test case
        1) test result 2) duration. All are strings
        '''
        for test_outcome in results:
            entry = self.find_entry(test_outcome[0])
            if entry is not None:
                entry.update(results, test_outcome)
            else:
                new_entry = CorrelationEntry(test_outcome[0])
                new_entry.update(results, test_outcome)
                self.table.append(new_entry)

    def evaluate_test_suite(self, test_suite, not_available=None):
        if not_available is None:
            not_available = []
        entries = list(filter(lambda x: x.get_name() in test_suite and x.get_name() not in not_available, self.table))
        execution_time = sum(list(map(lambda x: x.get_avg_duration(), entries)))
        dissimilarity = 0
        fail_prob = 0
        for entry in entries:
            fail_prob += entry.get_avg_fail()
            loc_sum = 0
            for other_entry in entries:
                loc_sum += entry.get_trust(other_entry)
            dissimilarity += loc_sum * entry.get_avg_fail()
        test_metric = dissimilarity / fail_prob
        return execution_time, test_metric

    def evaluate_test_suite_directed(self, test_suite, available):
        ts_entries = list(filter(lambda x: x.get_name() in test_suite, self.table))
        no_ts_entries = list(filter(lambda x: x.get_name() in available, self.table))
        # no_ts_entries = list(filter(lambda x: x.get_name() not in test_suite and x.get_name() in available, self.table))
        execution_time = sum(list(map(lambda x: x.get_avg_duration(), ts_entries)))
        fitness = 0
        '''
        norming_factor = len(no_ts_entries) * len(ts_entries)
        for ts_entry in ts_entries:
            for other_entry in no_ts_entries:
                fitness += ts_entry.get_approx_cond_prob(other_entry) * ts_entry.get_avg_fail()
        try:
            fitness = fitness / norming_factor
        except Exception as e:
            fitness = 0
        # add avg
        '''
        prob_sum = 0
        for ts_entry in ts_entries:
            prob_sum += ts_entry.get_avg_fail()
        if len(ts_entries) > 0:
            fitness += prob_sum / len(ts_entries)
        avg_fail_prob = fitness
        # add group coverage
        all = set(map(lambda x: x[:len(x) - len(x.split("\\")[-1]) - 1], list(map(lambda x: x.get_name(), no_ts_entries))))
        covered = set(map(lambda x: x[:len(x) - len(x.split("\\")[-1]) - 1], list(map(lambda x: x.get_name(), ts_entries))))
        coverage = len(covered) / len(all)
        assert len(covered) / len(all) <= 1.0
        fitness += len(covered) / len(all)
        return execution_time, fitness, avg_fail_prob, coverage

class OptimizationProblem:

    def __init__(self):
        self.encountered_test_cases = []
        self.available_test_cases = []
        self.not_available_test_cases = []
        self.failed_once = []
        self.correlation_table = CorrelationTable()

    def inject_new_results(self, json_path):
        results = JsonDataManager.load_data_from(json_path)["test_results"]
        # update table
        self.correlation_table.update_table(results)
        # add new test cases
        result_testcases = list(map(lambda x: x[0], results))
        new_testcases = list(filter(lambda x: x not in self.encountered_test_cases, result_testcases))
        self.encountered_test_cases.extend(new_testcases)

    def set_available_test_cases(self, other):
        self.available_test_cases = other
        self.failed_once = list(filter(lambda x: self.correlation_table.has_failed_once(x), self.available_test_cases))
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.available_test_cases = self.failed_once

        self.not_available_test_cases = list(filter(lambda x: x not in other, self.encountered_test_cases))

    def evaluate_tcs(self, binary_list):
        # ---> about fitness
        test_suite = []
        for i in range(0, len(binary_list)):
            if binary_list[i] == 1:
                test_suite.append(self.available_test_cases[i])
        return self.correlation_table.evaluate_test_suite_directed(test_suite, self.available_test_cases)

    def get_cost(self, index):
        tc = self.available_test_cases[index]
        return self.correlation_table.find_entry(tc).get_avg_duration()

    def get_percentage_of_found_errors(self, test_suite):
        raise Exception("not implemented")


class Solution:

    def __init__(self, opt_prob, initial=None):
        self.opt_prob = opt_prob
        if initial is None:
            self.vals = np.array(list(map(lambda x: 0, opt_prob.available_test_cases)))
        elif initial == "full":
            self.vals = np.array(list(map(lambda x: 1, opt_prob.available_test_cases)))
        else:
            self.vals = np.array(initial)
        cost, fitness, avg_fail_prob, coverage = self.opt_prob.evaluate_tcs(self.vals)
        self.cost = cost
        self.fitness = fitness
        self.avg_fail_prob = avg_fail_prob
        self.coverage = coverage
        self.objectives = [self.cost, self.fitness]

    def get_objectives(self):
        return self.objectives

    def dominates(self, other_sol):
        if self.cost < other_sol.cost and self.fitness >= other_sol.fitness:
            return True
        elif self.cost <= other_sol.cost and self.fitness > other_sol.fitness:
            return True
        else:
            return False

    def add_set(self, index):
        self.vals[index] = 1
        cost, fitness, avg_fail_prob, coverage = self.opt_prob.evaluate_tcs(self.vals)
        self.avg_fail_prob = avg_fail_prob
        self.coverage = coverage
        self.cost = cost
        self.fitness = fitness


class BSHOptProblem(OptimizationProblem):

    def __init__(self, job, init_to=5):
        super().__init__()
        self.job = job
        self.file_folder = "DATA" + os.sep + self.job.replace("/", "_")
        self.available_files = os.listdir(self.file_folder)
        self.counter = 0
        self.max_series = len(self.available_files)
        for i in range(0, init_to):
            print("step forward")
            self.step_forward()
        '''
        cor_tab = self.correlation_table
        import pickle
        with open('cor.pickle', 'wb') as handle:
            pickle.dump(cor_tab, handle, protocol=pickle.HIGHEST_PROTOCOL)
        print("hey")
        '''

    def step_forward(self):
        if self.counter < len(self.available_files):
            self.inject_new_results(self.file_folder + os.sep + self.available_files[self.counter])
            try:
                self.next = self.file_folder + os.sep + self.available_files[self.counter]
                self.next = JsonDataManager.load_data_from(self.next)["test_results"]
                result_testcases = list(map(lambda x: x[0], self.next))
                self.set_available_test_cases(result_testcases)
            except Exception as e:
                pass
            self.counter += 1
            return True
        else:
            return False

    def __get_groups(self, selected_tcs=None):
        if selected_tcs is None:
            tcs = list(map(lambda x: x[0], self.next))
        else:
            tcs = selected_tcs
        return list(set(map(lambda x: x[:len(x) - len(x.split("\\")[-1]) - 1], tcs)))

    def __get_filter_failed_groups(self, groups):
        failed = []
        for i in range(0, len(self.next)):
            tc = self.next[i][0]
            tc_group = tc[:len(tc) - len(tc.split("\\")[-1]) - 1]
            if tc_group in groups and self.next[i][1] == Constants.FAIL:
                failed.append(tc_group)
        return list(set(failed))

    def get_percentage_of_found_errors(self, test_suite):
        groups = self.__get_groups()
        total_failed = self.__get_filter_failed_groups(groups)
        selected = []
        for i in range(0, len(test_suite.vals)):
            if test_suite.vals[i] == 1:
                tc = self.available_test_cases[i]
                selected.append(tc)
                # selected.append(tc[:len(tc) - len(tc.split("\\")[-1]) - 1])
        selected = list(set(selected))
        found_failed = list(filter(lambda x: x[0] in selected and x[1] == Constants.FAIL, self.next))
        found_failed = list(map(lambda x: x[0], found_failed))
        selected = self.__get_groups(found_failed)
        # selected_failed = self.__get_filter_failed_groups(selected)
        try:
            return len(selected) / len(total_failed)
            # return len(selected_failed) / len(total_failed)
        except Exception as e:
            return 0.0

    def get_percentage_of_failed_tests(self, test_suite):
        selected = []
        for i in range(0, len(test_suite.vals)):
            if test_suite.vals[i] == 1:
                selected.append(self.available_test_cases[i])
        found_failed = list(filter(lambda x: x[0] in selected and x[1] == Constants.FAIL, self.next))
        total_failed = list(filter(lambda x: x[1] == Constants.FAIL, self.next))
        try:
            return len(found_failed) / len(total_failed)
        except Exception as e:
            return 0.0

    def get_coverage(self, solution):
        test_suite = []
        for i in range(0, len(solution.vals)):
            if solution.vals[i] == 1:
                test_suite.append(self.available_test_cases[i])
        no_ts_entries = list(filter(lambda x: x[0] not in test_suite, self.next))
        no_ts_entries = list(map(lambda x: x[0], no_ts_entries))
        # add group coverage
        covered = set(map(lambda x: x[:len(x) - len(x.split("\\")[-1]) - 1], list(map(lambda x: x, test_suite))))
        all = set(
            map(lambda x: x[:len(x) - len(x.split("\\")[-1]) - 1], list(map(lambda x: x, no_ts_entries))))
        return len(covered) / len(all)

    def get_greedy_next_coverage(self, solution):
        test_suite = []
        for i in range(0, len(solution.vals)):
            if solution.vals[i] == 1:
                test_suite.append(self.available_test_cases[i])
        covered = set(
            map(lambda x: x[:len(x) - len(x.split("\\")[-1]) - 1], list(map(lambda x: x, test_suite))))
        counter = 0
        for tc in self.available_test_cases:
            if tc not in test_suite:
                if not tc[:len(tc) - len(tc.split("\\")[-1]) - 1] in covered:
                    return counter
            counter += 1

    def get_greedy_next_fault(self, solution):
        test_suite = []
        for i in range(0, len(solution.vals)):
            if solution.vals[i] == 1:
                test_suite.append(self.available_test_cases[i])
        counter = 0
        best = None
        fault = 0.0
        for tc in self.available_test_cases:
            if tc not in test_suite:
                if self.correlation_table.find_entry(tc).get_avg_fail() > fault:
                    fault = self.correlation_table.find_entry(tc).get_avg_fail()
                    best = counter
            counter += 1
        return best


def has_converged(found, current, duration, adapted=False):
    factor = 1
    if adapted:
        factor = 2
    if found != -1:
        if current - found > (100 / factor):
            return True
    if duration > (300 / factor):
        return True
    return False

'''
import pickle
with open('cor.pickle', 'rb') as handle:
    b = pickle.load(handle)
tabelle = b.table
failed = list(filter(lambda x: x.total_fails > 0, tabelle))
for fail in failed:
    print(fail.test_name)
print(failed)
'''
