import numpy as np
import pytest

from itertools import product

import psyneulink as pnl
import psyneulink.core.llvm as pnlvm
import psyneulink.core.globals.keywords as kw

class TestReduce:

    @pytest.mark.function
    @pytest.mark.combination_function
    def test_single_array(self):
        R_function = pnl.core.components.functions.combinationfunctions.Reduce(operation=pnl.SUM)
        R_mechanism = pnl.ProcessingMechanism(function=pnl.core.components.functions.combinationfunctions.Reduce(operation=pnl.SUM),
                                              default_variable=[[1, 2, 3, 4, 5]],
                                              name="R_mechanism")

        assert np.allclose(R_function.execute([1, 2, 3, 4, 5]), [15.0])
        assert np.allclose(R_function.execute([[1, 2, 3, 4, 5]]), [15.0])
        assert np.allclose(R_function.execute([[[1, 2, 3, 4, 5]]]), [1, 2, 3, 4, 5])
        # assert np.allclose(R_function.execute([[[1, 2, 3, 4, 5]]]), [15.0])

        assert np.allclose(R_mechanism.execute([1, 2, 3, 4, 5]), [[15.0]])
        assert np.allclose(R_mechanism.execute([[1, 2, 3, 4, 5]]), [[15.0]])
        assert np.allclose(R_mechanism.execute([1, 2, 3, 4, 5]), [15.0])
        # assert np.allclose(R_mechanism.execute([[1, 2, 3, 4, 5]]), [15.0])

    @pytest.mark.function
    @pytest.mark.combination_function
    def test_column_vector(self):
        R_function = pnl.core.components.functions.combinationfunctions.Reduce(operation=pnl.SUM)
        R_mechanism = pnl.ProcessingMechanism(function=pnl.core.components.functions.combinationfunctions.Reduce(operation=pnl.SUM),
                                              default_variable=[[1], [2], [3], [4], [5]],
                                              name="R_mechanism")

        assert np.allclose(R_function.execute([[1], [2], [3], [4], [5]]), [1, 2, 3, 4, 5])
        # assert np.allclose(R_function.execute([[1], [2], [3], [4], [5]]), [15.0])
        assert np.allclose(R_function.execute([[[1], [2], [3], [4], [5]]]), [15.0])

        assert np.allclose(R_mechanism.execute([[1], [2], [3], [4], [5]]), [1, 2, 3, 4, 5])
        # assert np.allclose(R_mechanism.execute([[1], [2], [3], [4], [5]]), [15.0])

    @pytest.mark.function
    @pytest.mark.combination_function
    def test_matrix(self):
        R_function = pnl.core.components.functions.combinationfunctions.Reduce(operation=pnl.SUM)
        R_mechanism = pnl.ProcessingMechanism(function=pnl.core.components.functions.combinationfunctions.Reduce(operation=pnl.SUM),
                                              default_variable=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
                                              name="R_mechanism")

        assert np.allclose(R_function.execute([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), [6, 15, 24])
        assert np.allclose(R_function.execute([[[1, 2, 3], [4, 5, 6], [7, 8, 9]]]), [12, 15, 18])

        assert np.allclose(R_mechanism.execute([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), [6, 15, 24])

    # def test_heterogeneous_arrays(self):
    #     R_function = pnl.Reduce(operation=pnl.SUM)
    #     # R_mechanism = pnl.ProcessingMechanism(function=pnl.Reduce(operation=pnl.SUM),
    #     #                                       default_variable=[[1, 2], [3, 4, 5], [6, 7, 8, 9]],
    #     #                                       name="R_mechanism")
    #     print(R_function.execute([[1, 2], [3, 4, 5], [6, 7, 8, 9]]))
    #     print(R_function.execute([[[1, 2], [3, 4, 5], [6, 7, 8, 9]]]))
    #
    #     # print("mech = ", R_mechanism.execute([[1, 2], [3, 4, 5], [6, 7, 8, 9]]))
    #     # print("mech = ", R_mechanism.execute([[[1, 2], [3, 4, 5], [6, 7, 8, 9]]]))
    #     # print("mech = ", R_mechanism.execute([[[1, 2], [3, 4, 5], [6, 7, 8, 9]]]))
    #


SIZE=5
np.random.seed(0)
#This gives us the correct 2d array
test_var = np.random.rand(1, SIZE)
test_var2 = np.random.rand(2, SIZE)

RAND1_V = np.random.rand(SIZE)
RAND2_V = np.random.rand(SIZE)
RAND3_V = np.random.rand(SIZE)

RAND1_S = np.random.rand()
RAND2_S = np.random.rand()
RAND3_S = np.random.rand()

@pytest.mark.function
@pytest.mark.combination_function
@pytest.mark.parametrize("func", [pnl.core.components.functions.combinationfunctions.LinearCombination])
@pytest.mark.parametrize("variable", [test_var, test_var2])
@pytest.mark.parametrize("operation", [pnl.SUM, pnl.PRODUCT])
@pytest.mark.parametrize("exponents", [None, 2.0])
@pytest.mark.parametrize("weights", [None, 0.5, [[-1],[1]]])
@pytest.mark.parametrize("scale", [None, RAND1_S, RAND1_V])
@pytest.mark.parametrize("offset", [None, RAND2_S, RAND2_V])
@pytest.mark.parametrize("bin_execute", ['Python', 'LLVM', 'PTX'])
@pytest.mark.benchmark
def test_linear_combination_function(func, variable, operation, exponents, weights, scale, offset, bin_execute, benchmark):
    if bin_execute == 'PTX' and not pnlvm.ptx_enabled:
        benchmark(lambda _:0,0)
        benchmark.disabled = True
        pytest.skip("cuda not enabled/available")

    if weights is not None and not np.isscalar(weights) and  len(variable) != len(weights):
        pytest.skip("variable/weights mismatch")

    f = func(default_variable=variable, operation=operation, exponents=exponents, weights=weights, scale=scale, offset=offset)
    benchmark.group = "LinearCombinationFunction " + func.componentName;
    if (bin_execute == 'LLVM'):
        e = pnlvm.execution.FuncExecution(f)
        res = benchmark(e.execute, variable)
    elif (bin_execute == 'PTX'):
        e = pnlvm.execution.FuncExecution(f)
        res = benchmark(e.cuda_execute, variable)
    else:
        res = benchmark(f.function, variable)

    scale = 1.0 if scale is None else scale
    offset = 0.0 if offset is None else offset
    exponent = 1.0 if exponents is None else exponents
    weights = 1.0 if weights is None else weights

    tmp = (variable ** exponent) * weights
    if operation == pnl.SUM:
        expected = np.sum(tmp, axis=0) * scale + offset
    if operation == pnl.PRODUCT:
        expected = np.product(tmp, axis=0) * scale + offset

    assert np.allclose(res, expected)

# ------------------------------------

@pytest.mark.function
@pytest.mark.combination_function
@pytest.mark.parametrize("operation", [pnl.SUM, pnl.PRODUCT])
@pytest.mark.parametrize("input, input_states", [ ([[1,2,3,4]], ["hi"]), ([[1,2,3,4], [5,6,7,8], [9,10,11,12]], ['1','2','3']), ([[1, 2, 3, 4], [5, 6, 7, 8], [0, 0, 1, 2]], ['1','2','3']) ])
@pytest.mark.parametrize("scale", [None, 2.5, [1,2.5,0,0]])
@pytest.mark.parametrize("offset", [None, 1.5, [1,2.5,0,0]])
@pytest.mark.benchmark
def test_linear_combination_function_in_mechanism(operation, input, input_states, scale, offset, benchmark):
    f = pnl.core.components.functions.combinationfunctions.LinearCombination(default_variable=input, operation=operation, scale=scale, offset=offset)
    p = pnl.ProcessingMechanism(size=[len(input[0])] * len(input), function=f, input_states=input_states)
    benchmark.group = "CombinationFunction " + pnl.core.components.functions.combinationfunctions.LinearCombination.componentName + "in Mechanism"

    res = benchmark(f.execute, input)

    scale = 1.0 if scale is None else scale
    offset = 0.0 if offset is None else offset
    if operation == pnl.SUM:
        expected = np.sum(input, axis=0) * scale + offset
    if operation == pnl.PRODUCT:
        expected = np.product(input, axis=0) * scale + offset

    assert np.allclose(res, expected)

@pytest.mark.function
@pytest.mark.combination_function
@pytest.mark.parametrize("operation", [pnl.SUM, pnl.PRODUCT])
@pytest.mark.parametrize("input, input_states", [ ([[1,2,3,4]], ["hi"]), ([[1,2,3,4], [5,6,7,8], [9,10,11,12]], ['1','2','3']), ([[1, 2, 3, 4], [5, 6, 7, 8], [0, 0, 1, 2]], ['1','2','3']) ])
@pytest.mark.parametrize("scale", [None, 2.5, [1,2.5,0,0]])
@pytest.mark.parametrize("offset", [None, 1.5, [1,2.5,0,0]])
@pytest.mark.benchmark
def test_linear_combination_function_in_mechanism_llvm(operation, input, input_states, scale, offset, benchmark):
    f = pnl.core.components.functions.combinationfunctions.LinearCombination(default_variable=input, operation=operation, scale=scale, offset=offset)
    p = pnl.ProcessingMechanism(size=[len(input[0])] * len(input), function=f, input_states=input_states)
    benchmark.group = "CombinationFunction " + pnl.core.components.functions.combinationfunctions.LinearCombination.componentName + "in Mechanism"

    e = pnlvm.execution.FuncExecution(f)
    res = benchmark(e.execute, input)

    scale = 1.0 if scale is None else scale
    offset = 0.0 if offset is None else offset
    if operation == pnl.SUM:
        expected = np.sum(input, axis=0) * scale + offset
    if operation == pnl.PRODUCT:
        expected = np.product(input, axis=0) * scale + offset

    assert np.allclose(res, expected)

@pytest.mark.llvm
@pytest.mark.cuda
@pytest.mark.function
@pytest.mark.combination_function
@pytest.mark.parametrize("operation", [pnl.SUM, pnl.PRODUCT])
@pytest.mark.parametrize("input, input_states", [ ([[1,2,3,4]], ["hi"]), ([[1,2,3,4], [5,6,7,8], [9,10,11,12]], ['1','2','3']), ([[1, 2, 3, 4], [5, 6, 7, 8], [0, 0, 1, 2]], ['1','2','3']) ])
@pytest.mark.parametrize("scale", [None, 2.5, [1,2.5,0,0]])
@pytest.mark.parametrize("offset", [None, 1.5, [1,2.5,0,0]])
@pytest.mark.benchmark
def test_linear_combination_function_in_mechanism_ptx(operation, input, input_states, scale, offset, benchmark):
    f = pnl.core.components.functions.combinationfunctions.LinearCombination(default_variable=input, operation=operation, scale=scale, offset=offset)
    p = pnl.ProcessingMechanism(size=[len(input[0])] * len(input), function=f, input_states=input_states)
    benchmark.group = "CombinationFunction " + pnl.core.components.functions.combinationfunctions.LinearCombination.componentName + "in Mechanism"

    e = pnlvm.execution.FuncExecution(f)
    res = benchmark(e.cuda_execute, input)

    scale = 1.0 if scale is None else scale
    offset = 0.0 if offset is None else offset
    if operation == pnl.SUM:
        expected = np.sum(input, axis=0) * scale + offset
    if operation == pnl.PRODUCT:
        expected = np.product(input, axis=0) * scale + offset

    assert np.allclose(res, expected)
