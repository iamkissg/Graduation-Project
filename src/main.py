# -*- coding: utf-8 -*-

from __future__ import division

import random
from math import ceil
from collections import OrderedDict

import numpy as np
import mingus.extra.lilypond as lp
from deap import base
from deap import tools
from deap import creator
import mingus.core.intervals as intervals
from mingus.containers import Bar, Note, Track
from mingus.midi import midi_file_out

from util import get_geometric_progression_of_2
from config import pitch_frequencies, duration_frequencies

__author__ = "kissg"
__date__ = "2017-03-10"

VELOCITY = {16, 33, 49, 64, 80, 96, 112, 126}

# 适应度函数, `weights` weights 的每一项表示一个观测值
# 暂定为 (1.0,), 表示最大化协和度
creator.create("BarFitness", base.Fitness, weights=(1.0,))
creator.create("TrackFitness", base.Fitness, weights=(1.0,))

# 以小节为个体
# [[1, 5, 4], [1.5, 5, 4], [3, 5, 4], [5, 5, 4]]
creator.create("Bar", Bar, fitness=creator.BarFitness)
creator.create("Track", Track, fitness=creator.TrackFitness)


def gen_pitch(min=0, max=107):
    '''
    :param min: minimum scientific note name
    :param max: maximum scientific note name
    :return: mingus.containers.Note
    '''
    return Note().from_int(
        np.random.choice(range(min, max + 1), p=pitch_frequencies))


def gen_duration(min=32, max=1):
    '''
    The parameters may be confusing. However 1 represents a whote note ,
    2 a half note, 4 a quarter note, etc.
    :return: a duration of note
    '''
    available_durations = get_geometric_progression_of_2(max, min)
    probabilities = duration_frequencies[-len(available_durations):]
    p_sum = sum(probabilities)
    p = [_ / p_sum for _ in probabilities]

    # todo - better probabilities
    d = np.random.choice(available_durations, p=p)
    return d


def gen_bar(key="C", meter=(4, 4)):
    bar = Bar(key, meter)
    while not bar.is_full():
        # todo - place rest
        bar.place_notes(toolbox.note(),
                        gen_duration(max=int(ceil(bar.value_left()))))
    return bar


def gen_track(bars):
    # todo - another approach
    track = Track()
    for bar in bars:
        track.add_bar(bar)
    return track


def grade_intervals(note1, note2):
    """
    对音程打分 -
    纯一度或纯八度, 为极协和音程,
    纯四度或纯五度, 协和音程,
    大三度, 小三度, 大六度, 小六度, 不完全协和音程
    以上属于相对协和音程
    大二度, 小二度, 大七度, 小七度, 不协和音程
    其他为极不协和音程
    """
    itv = intervals.determine(note1, note2)
    if "unison" in itv:  # 纯一度, 纯八度
        return 5
    elif itv in ("perfect fifth", "perfect fourth"):
        return 4
    elif itv in ("major third", "minor third", "major sixth", "minor sixth"):
        return 3
    elif itv in ("major second", "minor second", "major seventh", "minor seventh"):
        return -1
    else:
        return -3


def grade_octave(octave1, octave2):
    """
    对八度打分 - 度数小于在一个八度内的, 打 1 分； 否则 0 分
    """
    if abs(octave1 - octave2) < 2:
        return 1
    else:
        return 0


def grade_duration(duration1, duration2):
    """
    对时值打分 - 时值变化剧烈 (超过 4 倍), 0 分
    """
    if max(duration1 / duration2, duration2 / duration1) > 4:
        return 0
    else:
        return 1


def grade_pitch_change(bar):
    """
    对整体音高变化的打分 - 单调变化或不变的音高, 低分
    """
    # todo
    pass


def grade_duration_change(bar):
    """
    对整体时值变化的打分 - 单调的时值, 缺少节奏感, 低分
    """
    # todo
    pass


def grade_internal_chords(bar):
    """
    对调内三/七和弦的打分
    """
    # todo
    pass


def evalute_bar(bar):
    # todo - kinds of evalute ways
    return bar.get_note_names()


def evaluate_track(individual):
    # Do some hard computing on the individual
    # Multi dimension
    return 1


toolbox = base.Toolbox()
# 此处随机生成种群的个体
# 注: toolbox.register(alias, func, args_for_func)
# 注: tools.initRepeat(container, generator_func, repeat_times)
toolbox.register("note", gen_pitch, min=9, max=96)  # 钢琴共 88 键, A0 ~ C8
toolbox.register("bar", gen_bar, key="C", meter=(4, 4))
toolbox.register("track", gen_track)

bars = [toolbox.bar() for i in range(16)]
track = toolbox.track(bars)
lp.to_pdf(lp.from_Track(track), "1.pdf")

midi_file_out.write_Track("1.mid", track)
