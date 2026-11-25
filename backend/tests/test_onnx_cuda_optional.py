"""Exercise an actual CUDA ONNX kernel; the toy graph is created in memory."""
import numpy as np
import pytest


def test_onnx_runtime_cuda_executes_without_cpu_fallback():
    torch=pytest.importorskip('torch')
    if not torch.cuda.is_available():pytest.skip('CUDA runtime is not configured')
    ort=pytest.importorskip('onnxruntime')
    onnx=pytest.importorskip('onnx')
    if 'CUDAExecutionProvider' not in ort.get_available_providers():
        pytest.fail('GPU environment lacks ONNX Runtime CUDA provider')
    # Importing torch first loads the matching CUDA/cuDNN runtime libraries.
    from onnx import helper,TensorProto
    graph=helper.make_graph([helper.make_node('MatMul',['a','b'],['result'])],
                            'rvectr-runtime-check',
                            [helper.make_tensor_value_info(name,TensorProto.FLOAT,[2,2]) for name in ['a','b']],
                            [helper.make_tensor_value_info('result',TensorProto.FLOAT,[2,2])])
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',13)],ir_version=8)
    options=ort.SessionOptions()
    options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
    session=ort.InferenceSession(model.SerializeToString(),sess_options=options,providers=['CUDAExecutionProvider'])
    a=np.asarray([[1,2],[3,4]],dtype=np.float32)
    b=np.asarray([[2,0],[0,2]],dtype=np.float32)
    assert np.allclose(session.run(None,{'a':a,'b':b})[0],a@b)
