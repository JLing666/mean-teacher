# Copyright (c) 2018, Curious AI Ltd. All rights reserved.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to
# Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""CIFAR-10 supervised baselines. Train with all training data, evaluate against test set."""

import logging
import sys

from .run_context import RunContext
import tensorflow as tf

from datasets import Cifar10ZCA
from mean_teacher.model import Model
from mean_teacher import minibatching


LOG = logging.getLogger('main')


def parameters():
    test_phase = True
    for n_labeled in [4000]: #, 2000, 1000]:
        for data_seed in range(1): # 10
            epochs = 750
            rampdown_epochs = 100
            yield {
                'test_phase': test_phase,
                'n_labeled': n_labeled,
                'data_seed': data_seed,
                'training_length': epochs * n_labeled / 100,
                'rampdown_length': rampdown_epochs * n_labeled / 100
            }

    for data_seed in range(0): # 4
        yield {
            'test_phase': test_phase,
            'n_labeled': 'all',
            'data_seed': data_seed,
            'training_length': 150000,
            'rampdown_length': 25000
        }


def run(test_phase, data_seed, n_labeled, training_length, rampdown_length):
    minibatch_size = 100
    n_labeled_per_batch = 100

    tf.reset_default_graph()
    model = Model(RunContext(__file__, data_seed))

    cifar = Cifar10ZCA(n_labeled=n_labeled,
                       data_seed=data_seed,
                       test_phase=test_phase)

    model['flip_horizontally'] = True
    model['ema_consistency'] = True
    model['max_consistency_cost'] = 0.0
    model['apply_consistency_to_labeled'] = False
    model['adam_beta_2_during_rampup'] = 0.999
    model['ema_decay_during_rampup'] = 0.999
    model['normalize_input'] = False  # Keep ZCA information
    model['rampdown_length'] = rampdown_length
    model['training_length'] = training_length

    training_batches = minibatching.training_batches(cifar.training,
                                                     minibatch_size,
                                                     n_labeled_per_batch)
    evaluation_batches_fn = minibatching.evaluation_epoch_generator(cifar.evaluation,
                                                                    minibatch_size)

    tensorboard_dir = model.save_tensorboard_graph()
    LOG.info("Saved tensorboard graph to %r", tensorboard_dir)

    model.train(training_batches, evaluation_batches_fn)


if __name__ == "__main__":
    for run_params in parameters():
        run(**run_params)
