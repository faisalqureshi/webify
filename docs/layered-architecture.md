---
subtitle: Advanced Topics in High-Performance Computing
title: Layered Architectures
author: Faisal Qureshi
institute:
date:
sansfont: Gill Sans
slide-numbers: true
fontsize: 10pt
vertical: t
titlegraphic: uoit-logo.pdf
include-in-header: header.latex
template: 
to: beamer
copy-to-destination: True

---

# Logistic regression and layers

Lets look at how we can specify logistic regression as layers.  The ability to specify such models as layers is key to designing neural networks.  We will also discuss *backpropagation*.

# Example: 2-class softmax classifier

**Negative log likelihood**

$$
\scriptstyle
\begin{split}
l(\theta) = - \sum_{i=1}^N \mathbb{I}_0 (y^{(i)}) \log
\frac{e^{\bx^{(i)^T} \theta_1}}{e^{\bx^{(i)^T} \theta_1} + {e^{\bx^{(i)^T} \theta_2}}}
+
\mathbb{I}_1 (y^{(i)}) \log
\frac{e^{\bx^{(i)^T} \theta_2}}{e^{\bx^{(i)^T} \theta_1} + {e^{\bx^{(i)^T} \theta_2}}}
\end{split}
$$

\alert{Define cost $C(\theta)$ that we want to minimize to be the negative log likelihood $l(\theta)$.}

**Layer representation**
\begin{figure}
\centerline{
\includegraphics[width=10cm]{logistic-regression/softmax-2classes-layers.pdf}
}
\end{figure}


# Chain rule

$$
\frac{\partial f(g(u,v),h(u,v))}{\partial u} = \diff{f}{g} \diff{g}{u} + \diff{f}{h} \diff{h}{u}
$$

\begin{figure}
\centerline{
\includegraphics[width=6cm]{logistic-regression/chain-rule.png}
}
\end{figure}

# Example: 2-class softmax classifier

We can use the *chain rule* to compute $\frac{\partial z^4}{\partial \theta_1}$ and $\frac{\partial z^4}{\partial \theta_2}$.  

\begin{figure}
\centerline{
\includegraphics[width=7cm]{logistic-regression/chain-rule-z4.pdf}
}
\end{figure}

We can similarly compute $\frac{\partial z^4}{\partial \theta_2}$.

Recall that $z^4 = l(\theta)$, and we can minimize the $l(\theta)$ using gradient descent using the gradients computed above.

# Example: 2-class softmax classifier (layered view)

\vspace{.5cm}

\begin{figure}
\centerline{
\includegraphics[width=8cm]{logistic-regression/softmax-2classes-layers2.pdf}
}
\end{figure}

\vspace{-.6cm}

\begincols

\column{.7 \textwidth}

**Forward pass**

$z^1 = f(\mathbf{x})$ (*input data*)\
$z^2 = f(z^1)$ (*linear function*)\
$z^3 = f(z^2)$ (*log softmax*)\
$z^4 = f(z^3) = l(\theta)$ (*negative log likelihood*, cost)

\column{.3 \textwidth}

**Backward pass**

$\delta^l = \diff{l(\theta)}{z^L}$

\stopcols

# Example: 2-class softmax classifier (layered view)

**Computing $\delta^l$**
$$
\begin{split}
\delta^4 &= \diff{C({\theta})}{z^4} = \diff{z^4}{z^4} = 1 \\
\delta^3_1 &= \diff{C(\theta)}{z^3_1} = \diff{C(\theta)}{z^4} \diff{z^4}{z^3_1}
= \delta^4 \diff{z^4}{z^3_1} \\
\delta^3_2 &= \diff{C(\theta)}{z^3_2} = \diff{C(\theta)}{z^4} \diff{z^4}{z^3_2}
= \delta^4 \diff{z^4}{z^3_2} \\
\delta^2_1 &= \diff{C(\theta)}{z^2_1} = \sum_k \diff{C(\theta)}{z^3_k} \diff{z^3_k}{z^2_1} = \sum_k \delta^3_k \diff{z^3_k}{z^2_1} \\
\delta^2_2 &= \diff{C(\theta)}{z^2_2} = \sum_k \diff{C(\theta)}{z^3_k} \diff{z^3_k}{z^2_2} = \sum_k \delta^3_k \diff{z^3_k}{z^2_2}
\end{split}
$$

# For any differentiable layer $l$

\begincols

\column{.6 \linewidth}

For a given layer $l$, with inputs $z_i^l$ and outputs $z_k^{l+1}$
$$
\delta^l_i = \sum_k \delta^{l+1}_k \diff{z^{l+1}_k}{z^l_i}
$$

Similarly, for layer $l$ that depends upon parameters $\theta^l$,
$$
\diff{C(\theta)}{\theta^l} = \sum_k \diff{C(\theta)}{z^{l+1}_k} \diff{z^{l+1}_k}{\theta^l} = \sum_k \delta^{l+1}_k \diff{z^{l+1}_k}{\theta^l}
$$

*In our 2-class softmax classifier only layer 1 has parameters ($\theta_0$ and $\theta_1$).*


\column{.4 \linewidth}

\begin{figure}
\centerline{
\includegraphics[width=5cm]{logistic-regression/layer-l.png}
}
\end{figure}

\stopcols

# Layered architectures

As long as we have differentiable layers, i.e., we can compute $\diff{z^{l+1}_k}{z^{l}_i}$,
we can use *backpropagation* to update the parameters $\theta$ to minimize the cost $C(\theta)$.

\vspace{.5cm}

\begin{figure}
\centerline{
\includegraphics[width=12cm]{logistic-regression/layer-architecture.pdf}
}
\end{figure}

# Backpropagation

- Set $z^1$ equal to input $\mathbf{x}$.
- Forward pass: compute $z^2, z^3, ...$ layers $1, 2, ...$ activations.
- Set $\delta$ at the last layer equal to 1
- Backward pass: backpropagate $delta$s all the way to first layer.
- Update $\theta$
- Repeat

# Summary

- Layered view of logistic regression and softmax
- Backpropogation
