"""
Testing Recursive feature elimination
"""

import numpy as np
from numpy.testing import assert_array_almost_equal, assert_array_equal
from nose.tools import assert_equal, assert_true
from scipy import sparse

from sklearn.feature_selection.rfe import RFE, RFECV
from sklearn.datasets import load_iris, make_friedman1
from sklearn.metrics import zero_one_loss
from sklearn.svm import SVC, SVR

from sklearn.utils import check_random_state
from sklearn.utils.testing import ignore_warnings
from sklearn.utils.testing import assert_warns_message

from sklearn.metrics import make_scorer
from sklearn.metrics import get_scorer

class MockClassifier(object):
    """
    Dummy classifier to test recursive feature ellimination
    """

    def __init__(self, foo_param=0):
        self.foo_param = foo_param

    def fit(self, X, Y):
        assert_true(len(X) == len(Y))
        self.coef_ = np.ones(X.shape[1], dtype=np.float64)
        return self

    def predict(self, T):
        return T.shape[0]

    predict_proba = predict
    decision_function = predict
    transform = predict

    def score(self, X=None, Y=None):
        if self.foo_param > 1:
            score = 1.
        else:
            score = 0.
        return score

    def get_params(self, deep=True):
        return {'foo_param': self.foo_param}

    def set_params(self, **params):
        return self


def test_rfe_set_params():
    generator = check_random_state(0)
    iris = load_iris()
    X = np.c_[iris.data, generator.normal(size=(len(iris.data), 6))]
    y = iris.target
    clf = SVC(kernel="linear")
    rfe = RFE(estimator=clf, n_features_to_select=4, step=0.1)
    y_pred = rfe.fit(X, y).predict(X)

    clf = SVC()
    rfe = RFE(estimator=clf, n_features_to_select=4, step=0.1,
              estimator_params={'kernel': 'linear'})
    y_pred2 = rfe.fit(X, y).predict(X)
    assert_array_equal(y_pred, y_pred2)


def test_rfe_deprecation_estimator_params():
    deprecation_message = ("The parameter 'estimator_params' is deprecated as of version 0.16 "
                           "and will be removed in 0.18. The parameter is no longer "
                           "necessary because the value is set via the estimator initialisation "
                           "or set_params function.")
    generator = check_random_state(0)
    iris = load_iris()
    X = np.c_[iris.data, generator.normal(size=(len(iris.data), 6))]
    y = iris.target
    assert_warns_message(DeprecationWarning, deprecation_message,
                         RFE(estimator=SVC(), n_features_to_select=4, step=0.1,
                             estimator_params={'kernel': 'linear'}).fit,
                         X=X,
                         y=y)

    assert_warns_message(DeprecationWarning, deprecation_message,
                         RFECV(estimator=SVC(), step=1, cv=5,
                               estimator_params={'kernel': 'linear'}).fit,
                         X=X,
                         y=y)


def test_rfe():
    generator = check_random_state(0)
    iris = load_iris()
    X = np.c_[iris.data, generator.normal(size=(len(iris.data), 6))]
    X_sparse = sparse.csr_matrix(X)
    y = iris.target

    # dense model
    clf = SVC(kernel="linear")
    rfe = RFE(estimator=clf, n_features_to_select=4, step=0.1)
    rfe.fit(X, y)
    X_r = rfe.transform(X)
    clf.fit(X_r, y)
    assert_equal(len(rfe.ranking_), X.shape[1])

    # sparse model
    clf_sparse = SVC(kernel="linear")
    rfe_sparse = RFE(estimator=clf_sparse, n_features_to_select=4, step=0.1)
    rfe_sparse.fit(X_sparse, y)
    X_r_sparse = rfe_sparse.transform(X_sparse)

    assert_equal(X_r.shape, iris.data.shape)
    assert_array_almost_equal(X_r[:10], iris.data[:10])

    assert_array_almost_equal(rfe.predict(X), clf.predict(iris.data))
    assert_equal(rfe.score(X, y), clf.score(iris.data, iris.target))
    assert_array_almost_equal(X_r, X_r_sparse.toarray())


def test_rfe_mockclassifier():
    generator = check_random_state(0)
    iris = load_iris()
    X = np.c_[iris.data, generator.normal(size=(len(iris.data), 6))]
    y = iris.target

    # dense model
    clf = MockClassifier()
    rfe = RFE(estimator=clf, n_features_to_select=4, step=0.1)
    rfe.fit(X, y)
    X_r = rfe.transform(X)
    clf.fit(X_r, y)
    assert_equal(len(rfe.ranking_), X.shape[1])
    assert_equal(X_r.shape, iris.data.shape)


def test_rfecv():
    generator = check_random_state(0)
    iris = load_iris()
    X = np.c_[iris.data, generator.normal(size=(len(iris.data), 6))]
    y = list(iris.target)   # regression test: list should be supported

    # Test using the score function
    rfecv = RFECV(estimator=SVC(kernel="linear"), step=1, cv=5)
    rfecv.fit(X, y)
    # non-regression test for missing worst feature:
    assert_equal(len(rfecv.grid_scores_), X.shape[1])
    assert_equal(len(rfecv.ranking_), X.shape[1])
    X_r = rfecv.transform(X)

    # All the noisy variable were filtered out
    assert_array_equal(X_r, iris.data)

    # same in sparse
    rfecv_sparse = RFECV(estimator=SVC(kernel="linear"), step=1, cv=5)
    X_sparse = sparse.csr_matrix(X)
    rfecv_sparse.fit(X_sparse, y)
    X_r_sparse = rfecv_sparse.transform(X_sparse)
    assert_array_equal(X_r_sparse.toarray(), iris.data)

    # Test using a customized loss function
    scoring = make_scorer(zero_one_loss, greater_is_better=False)
    rfecv = RFECV(estimator=SVC(kernel="linear"), step=1, cv=5,
                  scoring=scoring)
    ignore_warnings(rfecv.fit)(X, y)
    X_r = rfecv.transform(X)
    assert_array_equal(X_r, iris.data)

    # Test using a scorer
    scorer = get_scorer('accuracy')
    rfecv = RFECV(estimator=SVC(kernel="linear"), step=1, cv=5,
                  scoring=scorer)
    rfecv.fit(X, y)
    X_r = rfecv.transform(X)
    assert_array_equal(X_r, iris.data)

    # Test fix on grid_scores
    def test_scorer(estimator, X, y):
        return 1.0
    rfecv = RFECV(estimator=SVC(kernel="linear"), step=1, cv=5,
                  scoring=test_scorer)
    rfecv.fit(X, y)
    assert_array_equal(rfecv.grid_scores_, np.ones(len(rfecv.grid_scores_)))

    # Same as the first two tests, but with step=2
    rfecv = RFECV(estimator=SVC(kernel="linear"), step=2, cv=5)
    rfecv.fit(X, y)
    assert_equal(len(rfecv.grid_scores_), 6)
    assert_equal(len(rfecv.ranking_), X.shape[1])
    X_r = rfecv.transform(X)
    assert_array_equal(X_r, iris.data)

    rfecv_sparse = RFECV(estimator=SVC(kernel="linear"), step=2, cv=5)
    X_sparse = sparse.csr_matrix(X)
    rfecv_sparse.fit(X_sparse, y)
    X_r_sparse = rfecv_sparse.transform(X_sparse)
    assert_array_equal(X_r_sparse.toarray(), iris.data)


def test_rfecv_mockclassifier():
    generator = check_random_state(0)
    iris = load_iris()
    X = np.c_[iris.data, generator.normal(size=(len(iris.data), 6))]
    y = list(iris.target)   # regression test: list should be supported

    # Test using the score function
    rfecv = RFECV(estimator=MockClassifier(), step=1, cv=5)
    rfecv.fit(X, y)
    # non-regression test for missing worst feature:
    assert_equal(len(rfecv.grid_scores_), X.shape[1])
    assert_equal(len(rfecv.ranking_), X.shape[1])


def test_rfe_min_step():

    n_features = 10
    X, y = make_friedman1(n_samples=50, n_features=n_features, random_state=0)
    n_samples, n_features = X.shape
    estimator = SVR(kernel="linear")

    # Test when floor(step * n_features) <= 0
    selector = RFE(estimator, step=0.01)
    sel = selector.fit(X,y)
    assert_equal(sel.support_.sum(), n_features // 2)

    # Test when step is between (0,1) and floor(step * n_features) > 0
    selector = RFE(estimator, step=0.20)
    sel = selector.fit(X,y)
    assert_equal(sel.support_.sum(), n_features // 2)

    # Test when step is an integer
    selector = RFE(estimator, step=5)
    sel = selector.fit(X,y)
    assert_equal(sel.support_.sum(), n_features // 2)
