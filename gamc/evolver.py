# -*- coding: utf-8 -*-

from __future__ import division

import random
from copy import deepcopy
import array
import math

import numpy as np
from deap import creator
from deap import tools
from deap import base

# import fortin2013
import engine2017 as fortin2013
import evaluate
import crossover
import mutation

import util
from statistics import duration_frequencies as duration_probability
from statistics import new_pitch_frequencies_ls as pitch_probability
import abcparse

__author__ = "kissg"
__date__ = "2017-03-10"

creator.create("BarFitness", base.Fitness, weights=(1.0, 1.0, 1.0, 1.0, 1.0, ))
# pitch.duration
creator.create("Bar", array.array, typecode="d", fitness=creator.BarFitness)

toolbox = base.Toolbox()

PITCH_LOW, PITCH_UP = 0, 96
DURATION_RANGE = [1, 2, 4, 8, 16, 32]


def get_pitch():
    # return random.randint(low, up)
    # pitch = np.random.choice(range(0, 88), p=pitch_probability)
    # return pitch if 36 <= pitch <= 83 else get_pitch()
    pitch = np.random.choice([
        36, 38, 40, 41, 43, 45, 47, 48, 50, 52, 53, 55, 57, 59, 60, 62, 64, 65, 67, 69
    ])
    return pitch


def get_duration(_range):
    available_probability = duration_probability[-len(_range):]
    new_total = sum(available_probability)
    probality = [_ / new_total for _ in available_probability]  # 重新计算比例
    duration = np.random.choice(_range, p=probality)
    return duration


def init_bar():
    rest = 1
    ind_bar = creator.Bar()
    while rest:
        pitch = get_pitch()
        duration = get_duration(
            [dt for dt in range(int(math.ceil(1 / rest)), 65, 1) if
             dt in DURATION_RANGE])
        ind_bar.append(pitch + duration / 100)
        rest -= 1 / duration
    return ind_bar


toolbox.register("ind_bar", init_bar)
toolbox.register("pop_bar", tools.initRepeat, list, toolbox.ind_bar)

toolbox.register("evaluate_bar", evaluate.evaluate_bar)
toolbox.register("mate_bar", crossover.cx_one_point_bar)
toolbox.register("mutate_bar", mutation.mutate_bar)
toolbox.register("preselect_bar", fortin2013.selTournamentFitnessDCD)
toolbox.register("select_bar", fortin2013.selNSGA2)


def evolve_bar(pop=None, ngen=100, mu=100, cxpb=0.9, mutpb=0.1, seed=None):
    """
    :param pop: population, if None, pop_bar will be called for producing bars
    :param ngen: evolution times
    :param mu:
    :param cxpb: crossover probability
    :param seed:
    :return:
    """
    random.seed(seed)

    CATASTROPHE = 5  # catastrophe countdown
    SURVIVAL_SIZE = 10  # initial survival size

    # create and register statistics method
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean, axis=0)
    stats.register("std", np.std, axis=0)
    stats.register("max", np.max, axis=0)
    stats.register("min", np.min, axis=0)

    # create logbook for recording evolution info
    logbook = tools.Logbook()
    # evals in Chinese is 评价?
    logbook.header = "gen", "evals", "std", "min", "avg", "max"

    # not None means the pop is produced from abc file or keyboard
    if not pop:
        pop = toolbox.pop_bar(n=mu)

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in pop if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate_bar, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit
    # This is just to assign the crowding distance to the individuals
    # no actual selection is done
    pop = toolbox.select_bar(pop, len(pop))

    print("FUCK")
    # todo: for catastrophe
    top_inds = tools.selBest(pop, SURVIVAL_SIZE)  # top  individuals to survive

    record = stats.compile(pop)
    logbook.record(gen=0, evals=len(invalid_ind), **record)
    print(logbook.stream)

    # Begin the generational process
    for gen in range(1, ngen):
        # Vary the population
        offspring = toolbox.preselect_bar(pop, len(pop))
        offspring = [toolbox.clone(ind) for ind in offspring]

        for ind1, ind2 in zip(offspring[::2], offspring[1::2]):
            if random.random() <= cxpb:
                toolbox.mate_bar(ind1, ind2)

            toolbox.mutate_bar(ind1)
            toolbox.mutate_bar(ind2)
            del ind1.fitness.values, ind2.fitness.values

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate_bar, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # Select the next generation population
        pop = toolbox.select_bar(pop + offspring, mu)

        record = stats.compile(pop)
        logbook.record(gen=gen, evals=len(invalid_ind), **record)
        print(logbook.stream)

        # todo: for catastrophe
        if util.cal_variance(logbook.select("avg")[-2].tolist(),
                        logbook.select("avg")[-1].tolist()) < 0.01 and \
                        util.cal_variance(logbook.select("std")[-2].tolist(),
                                     logbook.select("std")[-1].tolist()) < 0.01:
            CATASTROPHE -= 1
            # top_inds = tools.selBest(pop, SURVIVAL_SIZE)  # 更新 top

        if CATASTROPHE == 0:
            print(("BOOM " * 10 + "\n") * 10)
            pop = toolbox.pop_bar(n=(mu - SURVIVAL_SIZE))
            pop.extend(deepcopy(top_inds))  # 灾变的新生个体

            invalid_ind = [ind for ind in pop if not ind.fitness.valid]
            fitnesses = toolbox.map(toolbox.evaluate_bar, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            pop = toolbox.select_bar(pop, len(pop))
            SURVIVAL_SIZE += 10  # 环境容纳量增大
            if SURVIVAL_SIZE == mu:
                return pop, logbook
            top_inds = tools.selBest(pop, SURVIVAL_SIZE)  # 更新 top

            CATASTROPHE = 5  # 重置灾变倒计时

    return pop, logbook


def evolve_sentence(bars_pool, ngen=20, mu=10, cxpb=0.9, seed=None):
    creator.create("SentenceFitness", base.Fitness,
                   weights=(1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0))
    creator.create("Sentence", list, fitness=creator.SentenceFitness,
                   bars_pool=[])

    toolbox.register("sentence", init_sentence, creator.Sentence,
                     bars_pool=bars_pool)
    toolbox.register("pop_sentence", tools.initRepeat, list, toolbox.sentence)

    toolbox.register("evaluate", evaluate.evaluate_sentence)
    toolbox.register("mate", crossover.cross_sentence)
    toolbox.register("mutate", mutation.mutate_sentence)
    toolbox.register("preselect", fortin2013.selTournamentFitnessDCD)
    toolbox.register("select", fortin2013.selNSGA2)
    random.seed(seed)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean)
    stats.register("std", np.std)
    stats.register("max", np.max)
    stats.register("min", np.min)

    logbook = tools.Logbook()
    logbook.header = "gen", "evals", "std", "min", "avg", "max"

    pop = toolbox.pop_sentence(n=mu)

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in pop if not ind.fitness.valid]

    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    # This is just to assign the crowding distance to the individuals
    # no actual selection is done
    pop = toolbox.select(pop, len(pop))

    record = stats.compile(pop)
    logbook.record(gen=0, evals=len(invalid_ind), **record)
    print(logbook.stream)

    # Begin the generational process
    for gen in range(1, ngen):
        # Vary the population
        offspring = toolbox.preselect(pop, len(pop))
        # offspring = [toolbox.clone(ind) for ind in offspring]
        for ind in offspring:
            toolbox.clone(ind)

        for ind1, ind2 in zip(offspring[::2], offspring[1::2]):
            if random.random() <= cxpb:
                toolbox.mate(ind1, ind2)

            toolbox.mutate(ind1)
            toolbox.mutate(ind2)
            del ind1.fitness.values, ind2.fitness.values

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # Select the next generation population
        pop = toolbox.select(pop + offspring, mu)
        record = stats.compile(pop)
        logbook.record(gen=gen, evals=len(invalid_ind), **record)
        print(logbook.stream)

    return pop, logbook


name2int = {
    "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
    "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11
}


def init_pop_from_seq(seq):
    ls = []
    for i in seq:
        rest = 1
        ind_bar = creator.Bar()
        while rest:
            ind_bar.append(i[0])
            rest -= i[1]
        ls.append(ind_bar)
    return ls


def evolve_from_abc(abc, ngen=100, mu=100, cxpb=0.9, mutpb=0.1):
    key, meter, notes = abcparse.parse_abc(abc)
    names, durations = zip(*
                           [(note[0].rstrip("*"), note[1]) for note in notes])
    names = [(name[:-1].upper(), int(name[-1])) for name in names]
    pitchs = [name[1] * 12 + name2int[name[0]] for name in names]
    prepare_pop = [(p + d / 100.0, 1.0 / d) for p, d in zip(pitchs, durations)]
    pop = init_pop_from_seq(prepare_pop)

    # ppb, dpb = count(names, durations)
    #
    # toolbox.unregister("mate_bar")
    # toolbox.unregister("mutate_bar")
    # toolbox.register("mate_bar", crossover.cross_bar, ppb=ppb, dpb=dpb)
    # toolbox.register("mutate_bar", mutation.mutate_bar, ppb=ppb, dpb=dpb)

    evolved_pop, log = evolve_bar(pop=pop, ngen=ngen, mu=mu, cxpb=cxpb,
                                  mutpb=mutpb)
    return evolved_pop, log


def evolve_from_keyboard(notes, durations, ngen=100, mu=100, cxpb=0.9,
                         mutpb=0.1):
    pop = construct_bars(notes, durations, container=creator.Bar)

    ppb, dpb = count(notes, durations)
    toolbox.unregister("mate_bar")
    toolbox.unregister("mutate_bar")
    toolbox.register("mate_bar", crossover.cross_bar, ppb=ppb, dpb=dpb)
    toolbox.register("mutate_bar", mutation.mutate_bar, ppb=ppb, dpb=dpb)
    evolved_pop, log = evolve_bar(pop=pop, mu=len(pop), ngen=ngen,
                                  cxpb=cxpb, mutpb=mutpb)
    evolved_pop, log = evolve_sentence(evolved_pop, mu=mu)
    evolved_pop = [bar for bar_list in evolved_pop for bar in bar_list]

    return evolved_pop, log


if __name__ == '__main__':
    bars_pool, log = evolve_from_abc(
        "/home/kissg/Developing/Graduation-Project/data/ABCs/999.abc")
    track2 = Track()
    for i, bar in enumerate(tools.selTournament(bars_pool, 16, 4)):
        track2.add_bar(bar)

    lp.to_pdf(lp.from_Track(track2), "top_bar.pdf")

    midi_file_out.write_Track("top_bar.mid", track2)
    # exit(0)
    key, meter, notes = parse_abc(
        "/home/kissg/Developing/Graduation-Project/data/ABCs/999.abc")
    notes, durations = zip(*[(note[0].rstrip("*"), note[1]) for note in notes])
    notes = [note[:-1].upper() + "-" + note[-1] for note in notes]

    # print(key, meter, notes, durations)

    pop = construct_bars(notes, durations, container=creator.Bar)
    track3 = Track()
    for i, bar in enumerate(pop, 16):
        track3.add_bar(bar)
    lp.to_pdf(lp.from_Track(track3), "origin.pdf")

    midi_file_out.write_Track("origin.mid", track3)
    # for p in pop:
    #     print(p)
    #     fluidsynth.play_Bar(p)

    toolbox.unregister("mate_bar")
    toolbox.unregister("mutate_bar")
    ppb, dpb = count(notes, durations)
    # print(ppb)
    toolbox.register("mate_bar", crossover.cross_bar, ppb=ppb, dpb=dpb)
    toolbox.register("mutate_bar", mutation.mutate_bar, indpb=0.10, ppb=ppb,
                     dpb=dpb)

    bars_pool, log_bar = evolve_bar(pop=pop)
    # print(
    #     "Best individual is: {}\n with fitness: {}".format(hof[0],
    #                                                        hof[0].fitness))
    # print(len(set(bars_pool)))
    track2 = Track()
    for i, bar in enumerate(tools.selTournament(bars_pool, 16, 4)):
        track2.add_bar(bar)

    lp.to_pdf(lp.from_Track(track2), "top_bar.pdf")

    midi_file_out.write_Track("top_bar.mid", track2)

    # toolbox.register("select", tools.selTournament, tournsize=3)

    pop_sentence, log_sentence = evolve_sentence()

    track = Track()
    for i, sentence in enumerate(tools.selRoulette(pop_sentence, 4)):
        for bar in sentence:
            track.add_bar(bar)

    lp.to_pdf(lp.from_Track(track), "top_sentence.pdf")

    midi_file_out.write_Track("top_sentence.mid", track)
    # exit(0)
