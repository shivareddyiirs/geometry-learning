"""
This script executes the task of estimating the number of inhabitants of a neighborhood to be under or over the
median of all neighborhoods, based solely on the geometry for that neighborhood. The data for this script can be
generated by running the prep/get-data.sh and prep/preprocess-neighborhoods.py scripts, which will take about an hour
or two.

This script itself will run for about twelve seconds depending on your hardware, if you have at least a recent i7 or
comparable.
"""

import multiprocessing
import os
import sys
from datetime import datetime

import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from topoml_util.slack_send import notify

SCRIPT_VERSION = '0.0.2'
SCRIPT_NAME = os.path.basename(__file__)
TIMESTAMP = str(datetime.now()).replace(':', '.')
TRAINING_DATA_FILE = '../../files/neighborhoods/neighborhoods_train.npz'
NUM_CPUS = multiprocessing.cpu_count() - 1 if multiprocessing.cpu_count() > 1 else 1

if __name__ == '__main__':  # this is to squelch warnings on scikit-learn multithreaded grid search
    train_loaded = np.load(TRAINING_DATA_FILE)
    train_fourier_descriptors = train_loaded['fourier_descriptors']
    train_above_or_below_median = train_loaded['above_or_below_median']

    scaler = StandardScaler().fit(train_fourier_descriptors)
    train_fourier_descriptors = scaler.transform(train_fourier_descriptors)
    clf = DecisionTreeClassifier()

    param_grid = {'max_depth': range(6, 13)}
    cv = StratifiedShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
    grid = GridSearchCV(
        DecisionTreeClassifier(),
        n_jobs=NUM_CPUS,
        param_grid=param_grid,
        verbose=10,
        cv=cv)

    print('Performing grid search on model...')
    print('Using %i threads for grid search' % NUM_CPUS)
    grid.fit(train_fourier_descriptors, train_above_or_below_median)
    print("The best parameters are %s with a score of %0.3f"
          % (grid.best_params_, grid.best_score_))

    print('Training model on best parameters...')
    clf = DecisionTreeClassifier(max_depth=grid.best_params_['max_depth'])
    clf.fit(train_fourier_descriptors, train_above_or_below_median)

    # Run predictions on unseen test data to verify generalization
    TEST_DATA_FILE = '../../files/neighborhoods/neighborhoods_test.npz'
    test_loaded = np.load(TEST_DATA_FILE)
    test_fourier_descriptors = test_loaded['fourier_descriptors']
    test_above_or_below_median = np.asarray(test_loaded['above_or_below_median'], dtype=int)
    test_fourier_descriptors = scaler.transform(test_fourier_descriptors)

    print('Run on test data...')
    predictions = clf.predict(test_fourier_descriptors)

    correct = 0
    for prediction, expected in zip(predictions, test_above_or_below_median):
        if all([pred == exp for pred, exp in zip(prediction, expected)]):
            correct += 1

    accuracy = correct / len(predictions)
    print('Test accuracy: %0.3f' % accuracy)

    message = 'test accuracy of {0}'.format(str(accuracy))
    notify(SCRIPT_NAME, message)
    print(SCRIPT_NAME, 'finished successfully')
