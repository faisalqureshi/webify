---
to: beamer
subtitle: Topics in Digital Modeling
title: Linear Regression
author: Faisal Qureshi
institute: 
date: 
sansfont: Gill Sans
slide-numbers: true
fontsize: 10pt
vertical: t
titlegraphic: /Users/faisal/Dropbox/Templates/uoit-logo.pdf
template: 
highlight-style: kate
include-in-header: header.latex

---

# Regression

\vfill
\centerline{
\includegraphics[width=.9\textwidth]{regression/boston-housing-data.png}
}
\vfill

# Regression

Consider data points $(x^{(1)}, y^{(1)}), (x^{(2)}, y^{(2)}), \cdots , (x^{(N)}, y^{(N)})$.  Our goal is to learn a function $f(x)$ that returns (predict) the value $y$ given an $x$.

\centerline{
\includegraphics[width=.9\textwidth]{regression/regression-example.pdf}
}

# Regression

Given data $D = \{(x^{(1)}, y^{(1)}), (x^{(2)}, y^{(2)}), \cdots , (x^{(N)}, y^{(N)})\}$, learn function $y=f(x)$.

- $x$ is the input feature.  In the example above, $x$ is 1-dimensional, however, in practice $x$ is often an $M$-dimensional vector.
- $y$ is the target output.  We assume that $y$ is continuous. $y$ is 1-dimensional (why?)

# Linear regression

We assume that a linear model of the form $y=f(x)=\theta_0 + \theta_1 x$ best describe our data.

\centerline{
\includegraphics[width=.9\textwidth]{regression/regression-example.pdf}
}

How do we determine the degree of "fit" of our model?

# Least squares error

Loss-cost-objective function measures the degree of fit of a model to a given data.  

A simple loss function is to sum the squared differences between the actual values $y^{(i)}$ and the predicted values $f(x^{(i)})$.  This is called the *least squares error*.

$$C(\theta_0, \theta_1) = \sum_{i=1}^N \left(y^{(i)} - f(x^{(i)}) \right)^2$$

Our task is to find values for $\theta_0$ and $\theta_1$ (model parameters) to minimize the cost.

\alert{We often refer to the predicted value as $\hat{y}$.  Specifically, 
$\hat{y}^{(i)} = f(x^{(i)})$.
}

# Least squares error

$$C(\theta_0, \theta_1) = \sum_{i=1}^N \left(y^{(i)} - f(x^{(i)}) \right)^2$$

\centerline{
\includegraphics[width=.9\textwidth]{regression/regression-example.pdf}
}

# Least squares error

$$(\theta_0,\theta_1) = \argmin_{(\theta_0,\theta_1)} \sum_{i=1}^N \left(y^{(i)} - f(x^{(i)}) \right)^2$$

This is a convex function.  We can solve for $\theta_0$ and $\theta_1$ by setting $\frac{\partial C}{\partial \theta_0}=0$ and $\frac{\partial C}{\partial \theta_1}=0$.

\begincols

\column{.5\linewidth}

\centerline{
\includegraphics[width=\textwidth]{regression/quadratic-error.pdf}
}

\column{.5\linewidth}

\stopcols

# Least squares error

$\theta_0 = \langle y \rangle - \theta_1 \langle x \rangle$

$\theta_1 = \left(\sum_{i=1}^N (y^{(i)} - \langle y \rangle ) x^{(i)} \right) / \left(\sum_{i=1}^N (x^{(i)} - \langle x \rangle ) x^{(i)} \right)$

\centerline{
\includegraphics[width=.9\textwidth]{regression/regression-solution.pdf}
}

# Linear least squares in higher dimensions

**Input feature:** $\mathbf{x}^{(i)} = \left(1, x_{1}^{(i)}, x_{2}^{(i)}, \cdots, x_{M}^{(i)} \right)^T$.  

For this discussion, we assume $x_{0}^{(i)}=1$ (just to simplify mathematical notation).

**Target feature:** $y^{(i)}$

**Parameters:** $\theta = \left( \theta_0, \theta_1, \cdots, \theta_M \right)^T
 \in \mathbb{R}^{(M+1)}$

**Model:** $f(\bx) = \bx^T \theta$

# Linear least squares in higher dimensions

**Loss:**

$$C(\theta) =  (\bY - \bX \theta)^T (\bY - \bX \theta)$$

\vspace{.5cm}

\begincols

\column{.6\linewidth}

$$
\bX = \left[ \begin{array}{ccc}
- & \bx_1^T & -\\
- & \bx_2^T & -\\
& \vdots & \\ 
- & \bx_N^T & -
\end{array}
\right] \in \mathbb{R}^{N \times (M+1)}
$$ 

$\bX$ is referred to as the *design matrix*.


\column{.4\linewidth}

$$
\bY = \left[ \begin{array}{c}
y_1 \\
y_2 \\
\vdots \\
y_N
\end{array}
\right] \in \mathbb{R}^{N \times 1}
$$

\stopcols

# Linear least squares in higher dimensions

Loss: $C(\theta) =  (\bY - \bX \theta)^T (\bY - \bX \theta)$

Solve $\theta$ by setting $\frac{\partial C}{\partial \theta} = 0$

Solution: $\hat \theta = (\bX^T \bX)^{-1} \bX^T \bY$

<!-- \begincols -->

<!-- \column{.75\textwidth} -->

<!-- Derivation: -->

<!-- \column{.25\textwidth} -->

<!-- Relevant results from matrix differentiation -->


<!-- $$\frac{\partial \bA \bx}{\partial \bx} = \bA^T$$ -->

<!-- $$\frac{\partial \bx^T \bA \bx}{\partial \bx} = 2 \bA^T \bx$$ -->

<!-- \stopcols -->

# Linear least squares

\centerline{
\includegraphics[width=.8\textwidth]{regression/plane-fitting-data.pdf}
}

\small 

~~~Python
X = np.vstack([np.ones(x.shape), x, y]).T
Y = np.vstack([z]).T
XtX = np.dot(X.T, X)
XtY = np.dot(X.T, Y)
theta = np.dot(np.linalg.inv(XtX), XtY)
~~~

<!-- # Boston housing dataset -->

<!-- Derived from information collected by the U.S. Census Service concerning housing in the area of Boston Mass.  Consists of the following 14 attributes. -->

<!-- $\bx$ has 13 dimensions. $y$ is the median value of occupied homes in 1000's. -->

<!-- ## Attributes -->

<!-- \tiny -->

<!-- 	- CRIM - per capita crime rate by town -->
<!-- 	- ZN - proportion of residential land zoned for lots over 25,000 sq.ft. -->
<!-- 	- INDUS - proportion of non-retail business acres per town. -->
<!-- 	- CHAS - Charles River dummy variable (1 if tract bounds river; 0 otherwise) -->
<!-- 	- NOX - nitric oxides concentration (parts per 10 million) -->
<!-- 	- RM - average number of rooms per dwelling -->
<!-- 	- AGE - proportion of owner-occupied units built prior to 1940 -->
<!-- 	- DIS - weighted distances to five Boston employment centres -->
<!-- 	- RAD - index of accessibility to radial highways -->
<!-- 	- TAX - full-value property-tax rate per 10,000 -->
<!-- 	- PTRATIO - pupil-teacher ratio by town -->
<!-- 	- $B - 1000(Bk - 0.63)^2$ where Bk is the proportion of blacks by town -->
<!-- 	- LSTAT - \% lower status of the population -->
<!-- 	- MEDV - Median value of owner-occupied homes in 1000's -->

<!-- ```python -->
<!-- from sklearn import datasets  -->
<!-- from sklearn import linear_model  -->
<!-- import matplotlib.pyplot as plt  -->
<!-- %matplotlib inline  -->
<!-- boston = datasets.load_boston()  -->
<!-- plt.figure()  -->
<!-- plt.plot(boston.data[:,6], boston.target,'.')  -->
<!-- plt.ylabel('Median value of owner occupied homes in 1000\'s')  -->
<!-- plt.xlabel('Average number of rooms per dwelling')  -->
<!-- plt.title('The Boston Housing Data')  -->
<!-- ```  -->


<!-- # Boston housing dataset  -->

<!-- ![regression/boston-1.pdf](regression/boston-1.pdf)  -->

# 

\vfill
\centerline{\LARGE{Exercise}}
\vfill


# Beyond lines and planes

How can we construct more complex models?

\centerline{
\includegraphics[width=.6\textwidth]{regression/non-linear-data.png}
}

- It is possible to construct more complex models by defining input features that are some combinations of the components of $\bx$.
- For example, in the 1D case, we can set an $m$ order polynomial function as follows:
$$f(x) = \sum_{i=0}^m \theta_i x^i$$

# Beyond lines and planes

There are many ways to make linear models more powerful while retaining their nice mathematical properties:

- By using non-linear, non-adaptive basis functions, we can get generalized linear models that learn non-linear mappings from input to output but are linear in their parameters – only the linear part of the model learns.
– By using kernel methods we can handle expansions of the raw data that use a huge number of non-linear, non-adaptive basis functions.
simple case.
- Linear models do have fundamental limitations, and these can't be used to solve all our AI problems.

(*from R. Urtasun*)

# Polynomial fitting

Note that the model is still linear in $\theta$.  We can still use the same least squares loss and use the same technique that we used for fitting a line in 1D to fit the polynomial.

\centerline{
\includegraphics[width=.4\textwidth]{regression/polyfit.png}
}

*How would you setup $\bX$ and $\bY$?*

<!-- \begincols -->

<!-- \column{.8\textwidth} -->

<!-- $ -->
<!-- \bX = -->
<!-- $ -->

<!-- \column{.2\textwidth} -->

<!-- $ -->
<!-- \bY =  -->
<!-- $ -->

<!-- \stopcols -->

# Basis functions

The idea explored in the previous slide can be extended further.  It is possible to introduce non-linearity in the system by using basis functions $\phi(.)$ as follows:
$$f(\bx) = \mathbf{\phi}(\bx)^T \theta$$

**Example:** 

For a cubic polynomial (in 1D)

$\phi_0(x) = 1$  
$\phi_1(x) = x$  
$\phi_2(x) = x^2$  
$\phi_3(x) = x^3$

Then

$f(x) = \left[ \begin{array}{cccc}
\phi_0(x) & \phi_1(x) & \phi_2(x) & \phi_3(x) \end{array}  \right]
\left[ \begin{array}{c}
\theta_0 \\ \theta_1 \\ \theta_2 \\ \theta_3 \end{array}  \right]$

# Basis functions

*Example continues from the previous slide*

Using the basis functions, the loss can be written as 
$$
C(\theta) = \left(\bY - \Phi^T \theta \right)^T \left(\bY - \Phi^T \theta \right)
$$

And the solution is
$$
\hat \theta = (\Phi^T \Phi)^{-1} \Phi^T \bY
$$

*How would you set up matrix $\Phi$?*

# Basis functions

Example basis functions:

- Sigmoids
- Gaussians
- Polynomials (as seen before)

Similar basis functions are also used in neural networks, however, there is a key difference.  Neural networks can also learn the "parameters" of the basis functions themselves.  Linear regression only learns the parameters $\theta$, i.e., the basis functions themselves are fixed.

\centerline{
    \includegraphics[width=5cm]{regression/gaussian.png}
    \includegraphics[width=5cm]{regression/sigmoid.png}
}



# Regularization

- Increasing input features can increase model complexity 
- We need an automatic way to select appropriate model complexity
- *Regularization* is the standard technique that is used to achieve this goal
- Use the following loss function that penalize squared parameters: $$C(\theta) = \left( \by - \bX \theta \right)^T \left( \by - \bX \theta \right) + \delta^2 \theta^T \theta$$
    - This is referred to as *ridge regression* in statistics.

\centerline{
    \includegraphics[width=6cm]{regression/regularization-0.png}
    \includegraphics[width=6cm]{regression/regularization-1.png}
}

# Regularization

Solving for $\theta$ using $$C(\theta) = \left( \by - \bX \theta \right)^T \left( \by - \bX \theta \right) + \delta^2 \theta^T \theta$$ yields $$\hat \theta = (\bX^T \bX + \delta^2 \bI_d)^{-1} \bX^T \bY$$

So far, we have seen solutions having the following form: $$\hat \theta = (\bX^T \bX)^{-1} \bX^T \bY$$  Inverting $\bX^T \bX$ can lead to problems, if the system of equations is ill conditioned.  A solution is to add a small element to the diagonal of $\bX^T \bX$.  Note that the above estimate (that we achieved using ridge regression is doing exactly that).

# Regularization and basis function

When using basis functions, we define the loss function (for ridge regression) as follows
$$
C(\theta) = \left( \by - \Phi \theta \right)^T \left( \by - \Phi \theta \right) + \delta^2 \theta^T \theta$$

And the solution is
$$\hat \theta = (\Phi^T \Phi + \delta^2 \bI_d)^{-1} \Phi^T \bY$$

# Other forms of regularizers

$$C(\theta) = \left( \by - \bX \theta \right)^T \left( \by - \bX \theta \right) + \delta^2 \| \theta \|_q^q$$

\centerline{
    \includegraphics[width=3cm]{regression/regularization-half.png}
    \includegraphics[width=3cm]{regression/regularization-1a.png}
}
\centerline{
    \includegraphics[width=3cm]{regression/regularization-2.png}
    \includegraphics[width=3cm]{regression/regularization-4.png}
}

# Data whitening

If different components (dimensions) of the training data has different units (say one is measured in meters, while the other is measured in kilograms), then the squared penalty terms (that appear in our cost function) have very different weights, which can lead to erroneous solutions.

One scheme to avoid this is to "whiten the data".  Input components have:

- unit variance; and
- no covariance

$$
\bX^T_\mathrm{whitened} = \left( \bX^T \bX \right)^{-\frac{1}{2}} \bX^T
$$

But what if two components are perfectly correlated?  

# Regression

- What model should we choose?
- What may be the best way to parameterize this model?
- How do we decide if our model "fits" the data well?
- What confidence we have that our model also fits the *unseen* data, i.e., generalization.
	- This is important for prediction.

# Fit error

- In general it is not possible (nor desirable, and more on this later) for a model to fit the data exactly.

- A model may not fit the data due to following reasons:
    - Imperfect data (noise present in the data)
    - Mislabeling (target errors)
    - Hidden attributes that may affect the target values, and which are not available to us during model fitting
    - Model may be too "simple"
    
# How do we decide how well our model will fit the *unseen* data?

- Divide available data (input data + target values) into *training* and *testing* sets
- Only *training set* is available during the model fitting phase
- Evaluate the trained model (*hypothesis*) on the test set

# Cross-Validation

1. Given training data $(x_{\mathrm{train}}, y_{\mathrm{train}})$ , pick a value for $\delta^2$, compute estimate $\hat{\theta}$

2. Compute predictions for training set $\hat{y}_{\mathrm{train}}$.

3. Compute predictions for test set $\hat{y}_{\mathrm{test}}$.

\begin{figure}
\centerline{
\includegraphics[width=9cm]{regression/cross-validation-table.pdf}
}
\end{figure}

# Cross-Validation

## Case 1

$\delta^2$ selection via Min-Max is accounting for the worst-case scenario.  This is appropropriate if, say, you are designing a safety critical system.

## Case 2

$\delta^2$ selection via picking the best average case is useful in cases when you want your system to work well on average, with the caveat that in some cases the system might fail miserably.

# K-fold cross-validation

- Split the training data into K folds
- For each fold $k \in {1, \cdots, K}$
    - Train the model on every fold **except** $k$
    - Test the model on fold $k$
    - Repeat in a round-robin fashion

Often $K$ is set between $5$ to $10$

\begin{figure}
\centerline{
\includegraphics[width=9cm]{regression/6-fold-cross-validation.pdf}}
\end{figure}

# Leave-one-out Cross Validation (LOOCV)

- Set $K$ equal to $N$, the number of data items.
- Train model on all data items except $i$.
- Use the left-out data item for test, and repeat in a round-robin fashion

# Bias vs. Variance

- High bias leads to *underfitting*
    - The model has failed to capture the relevant features in the data.  Perhaps the model is too simple!?

- High variance leads to *overfitting*
    - The model has latched on to the irrelevant features (say, noise) in the data.  
    - Such models to not generalize well beyond the training data.

This is one of the reasons why we rely upon cross-validation to get a sense of how our model will perform on *previously unseen* data.  This also suggests that unlike optimization where the sole purpose is to minimize the error, in training sometimes we accept larger training errors to achieve better generalization.

# Summary

- 1-D linear regression is a useful case-study that illustrates many of issues that arise in regression in higher dimensions and in more complex models

- Model selection
    - Simple models are unable to capture all important variations in the data
    - Complex models overfit.  Consequently, these do not generalize well.

- The quality of fit
    - Check whether or not the model generalizes, i.e., how does it perform on the test data that was not available to it during the training phase

- Minimizing loss (*optimization*)
    - Gradient descent (*to be discussed later*)
        - Batch update
        - Online or stochastic updates
    - Use analytical approaches when available

# Summary

- More data can improve performance only if the model is of sufficient complexity

