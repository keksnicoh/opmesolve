# [Q]uantum open system within [optical] regime
I created this library as a basic framework to perform GPU computations on different open quantum systems
within optical regime. A highly optimized integrator of the [optical master equation][1] is implemented.

A [QuTip][1] based integrator, equipped with unit tests, defines a reference implementation. The optimized integrator is based on OpenCL in order to perform integration on the GPU where a matrix element of the density operator is represented by a work-item. The OpenCL kernel was further optimized while the existing unit tests enhanced confidence that each iteration did not break the code.

For further details, [checkout the repository of my master thesis][3].

This project is not actively development anymore, if you want to use it, feel free to ask any questions.

## install

clone the repository and then

```
python3 -m pip install .
```


## run tests

To check whether the lib works your environment, use

```bash
pytest .
```

[1]: https://en.wikiversity.org/wiki/Open_Quantum_Systems/The_Quantum_Optical_Master_Equation
[2]: http://qutip.org/
[3]: xxx