import numpy as np
from abc import ABC, abstractmethod

class BaseLinearRegression(ABC):
    def __init__(self):
        self.W = None
        self.b = 0.0
        self.done_ = False

    @abstractmethod
    def fit(self, X:np.ndarray, y: np.ndarray):
        pass

    def predict(self, X: np.ndarray):
        return X @ self.W + self.b
    
class OlSLinearRegression(BaseLinearRegression):
    def __init__(self, fit_intercept: bool = True):
        self.fit_intercept = fit_intercept
        super().__init__()

    def _design(self, X):
        return np.c_[np.ones((X.shape[0], 1)), X] if self.fit_intercept else X

    def fit(self, X, y):
        Xd = self._design(X)
        w, *_ = np.linalg.lstsq(Xd, y, rcond=None) 
        if self.fit_intercept:
            self.b, self.W = float(w[0]), w[1:]
        else:
            self.b, self.W = 0.0, w
        self.done_ = True
        return self

class GradientDescentLinearRegression(BaseLinearRegression):
    def __init__(self, learning_rate, convergence_tol=1e-6, iterations = 1000):
        self.learning_rate = learning_rate
        self.convergence_tol = convergence_tol
        self.iterations = iterations
        super().__init__()

    def _initialize_parameters(self, n_features):
        self.W = np.random.randn(n_features,1) * 0.01
        self.b = 0

    def _compute_cost(self, predictions):
        m = len(predictions)
        cost = np.sum(np.square(predictions - self.y)) / (2 * m)
        return cost
    
    def _forward(self, X):
        return X @ self.W + self.b

    def _backward(self, predictions):
        m = len(predictions)
        error = predictions - self.y
        self.dW = (self.X.T @ error)/m
        self.db = np.sum(error)/m

    def fit(self, X, y):
        self.X = X
        self.y = np.asarray(y, dtype=float).reshape(-1, 1)
        self._initialize_parameters(X.shape[1])
        costs = []

        for i in range(self.iterations):
            predictions = self._forward(X)
            cost = self._compute_cost(predictions)
            self._backward(predictions)
            self.W -= self.learning_rate * self.dW
            self.b -= self.learning_rate * self.db
            costs.append(cost)

            if i > 0 and abs(costs[-1] - costs[-2]) < self.convergence_tol:
                break
        self.done_ = True
        return self

class RidgeRegression(BaseLinearRegression):
    def __init__(self, lam: float = 1.0):
        super().__init__()
        self.lam = lam  

    def fit(self, X: np.ndarray, y: np.ndarray):
        X_bias = np.c_[np.ones((X.shape[0], 1)), X]

        I = np.eye(X_bias.shape[1])
        I[0, 0] = 0  
        
        theta = np.linalg.inv(X_bias.T @ X_bias + self.lam * I) @ X_bias.T @ y

        self.b = float(theta[0])
        self.W = theta[1:]
        self.done_ = True
        return self

class LassoRegression(BaseLinearRegression):
    def __init__(self, lam: float = 0.1, max_iter: int = 1000, tol: float = 1e-4):
        super().__init__()
        self.lam = lam
        self.max_iter = max_iter
        self.tol = tol

    def fit(self, X: np.ndarray, y: np.ndarray):
        _, n = X.shape

        y = np.asarray(y, dtype=float).reshape(-1, 1)
        
        self.W = np.zeros((n, 1))
        self.b = np.mean(y)
        
        for _ in range(self.max_iter):
            W_old = self.W.copy()
            for j in range(n):

                y_pred = X @ self.W + self.b
                residual = y - y_pred + X[:, [j]] * self.W[j]

                rho = X[:, [j]].T @ residual
                z = np.sum(X[:, j] ** 2)

                if rho < -self.lam / 2:
                    self.W[j] = (rho + self.lam / 2) / z
                elif rho > self.lam / 2:
                    self.W[j] = (rho - self.lam / 2) / z
                else:
                    self.W[j] = 0.0

            if np.sum(np.abs(self.W - W_old)) < self.tol:
                break
        self.done_ = True
        return self

class ElasticNetRegression(BaseLinearRegression):
    def __init__(self, lam1=0.1, lam2=0.1, max_iter=1000, tol=1e-4):
        super().__init__()
        self.lam1 = lam1 
        self.lam2 = lam2  
        self.max_iter = max_iter
        self.tol = tol

    def fit(self, X: np.ndarray, y: np.ndarray):
        m, n = X.shape
        
        y = np.asarray(y, dtype=float).reshape(-1, 1)

        self.W = np.zeros((n, 1))
        self.b = float(np.mean(y))

        for _ in range(self.max_iter):
            W_old = self.W.copy()

            for j in range(n):

                y_pred = X @ self.W + self.b
                residual = y - y_pred + X[:, [j]] * self.W[j]

                rho = (X[:, [j]].T @ residual)[0, 0]

                z = np.sum(X[:, j] ** 2) + self.lam2

                if rho < -self.lam1:
                    self.W[j] = (rho + self.lam1) / z
                elif rho > self.lam1:
                    self.W[j] = (rho - self.lam1) / z
                else:
                    self.W[j] = 0.0

            if np.linalg.norm(self.W - W_old) < self.tol:
                break
        self.done_ = True
        return self
