import os

from datetime import datetime

import multiprocessing
import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit, GridSearchCV
from sklearn.preprocessing import StandardScaler, MinMaxScaler, Normalizer
from sklearn.svm import SVC

SCRIPT_VERSION = '0.0.2'
SCRIPT_NAME = os.path.basename(__file__)
TIMESTAMP = str(datetime.now()).replace(':', '.')
TRAINING_DATA_FILE = '../files/neighborhoods/neighborhoods_train.npz'

if __name__ == '__main__':  # this is to squelch warnings on scikit-learn multithreaded grid search
    num_cpus = multiprocessing.cpu_count() - 1 if multiprocessing.cpu_count() > 1 else 1

    train_loaded = np.load(TRAINING_DATA_FILE)
    train_fourier_descriptors = train_loaded['fourier_descriptors']
    above_or_below_median = train_loaded['above_or_below_median'][:, 0]
    above_or_below_median = np.reshape(above_or_below_median, (above_or_below_median.shape[0]))

    # Copy-paste from http://scikit-learn.org/stable/auto_examples/svm/plot_rbf_parameters.html#sphx-glr-auto-examples
    # -svm-plot-rbf-parameters-py

    # plot distribution of features
    # if clustered: whiten (standardscaler)
    # if uniform: normalize
    # normalizer = Normalizer()
    scaler = MinMaxScaler().fit(train_fourier_descriptors)
    train_fourier_descriptors = scaler.transform(train_fourier_descriptors)

    # C_range = np.logspace(-2, 10, 13)
    C_range = [1e-3, 1e-2, 1e-1, 1e0, 1e1]
    gamma_range = np.logspace(-9, 3, 13)
    param_grid = dict(gamma=gamma_range, C=C_range)
    cv = StratifiedShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
    grid = GridSearchCV(
        SVC(kernel='rbf', verbose=True),
        n_jobs=num_cpus,
        param_grid=param_grid, cv=cv)

    print('Performing grid search on model...')
    print('Using %i threads for grid search' % num_cpus)
    grid.fit(X=train_fourier_descriptors, y=above_or_below_median)

    print("The best parameters are %s with a score of %0.2f"
          % (grid.best_params_, grid.best_score_))

    # Run predictions on unseen test data to verify generalization
    TEST_DATA_FILE = '../files/neighborhoods/neighborhoods_test.npz'
    test_loaded = np.load(TEST_DATA_FILE)
    test_fourier_descriptors = test_loaded['fourier_descriptors']
    test_above_or_below_median = test_loaded['above_or_below_median'][:, 0]
    test_above_or_below_median = np.reshape(test_above_or_below_median, (test_above_or_below_median.shape[0]))
    test_fourier_descriptors = scaler.transform(test_fourier_descriptors)

    clf = SVC(C=grid.best_params_['C'], gamma=grid.best_params_['gamma'], verbose=True)
    clf.fit(X=train_fourier_descriptors, y=above_or_below_median)
    predictions = clf.predict(test_fourier_descriptors)

    correct = 0
    for prediction, expected in zip(predictions, test_above_or_below_median):
        if prediction == expected:
            correct += 1

    accuracy = correct / len(predictions)
    print('Test accuracy: %0.2f' % accuracy)
