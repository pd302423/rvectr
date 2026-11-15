"""Optional private-model consistency check; no model data is part of the tests."""
import numpy as np
import pytest
from rvectr.paths import RuntimePaths


def test_fast_joint_model_matches_official_smpl_for_arbitrary_root_rotation():
    torch=pytest.importorskip('torch')
    pytest.importorskip('smplx')
    try:
        paths=RuntimePaths.discover()
    except ImportError:
        pytest.skip('Install the declared environment to discover private model paths')
    if not ((paths.models/'smpl'/'SMPL_NEUTRAL.pkl').is_file() or
            (paths.models/'SMPL_NEUTRAL.pkl').is_file()):
        pytest.skip('Official user-supplied SMPL model is not configured')
    from rvectr.fitting import _load_model,_JointModel
    device='cuda' if torch.cuda.is_available() else 'cpu'
    model=_load_model(paths.models,device)
    optimized=_JointModel(model)
    generator=torch.Generator(device=device).manual_seed(7)
    beta=torch.randn(10,generator=generator,device=device)*.05
    orient=torch.tensor([[0,0,0],[np.pi/2,0,0],[0,.4,-.3]],dtype=torch.float32,device=device)
    pose=torch.randn((3,69),generator=generator,device=device)*.08
    translation=torch.tensor([[0,0,0],[1,2,3],[-.5,.2,.8]],dtype=torch.float32,device=device)
    with torch.no_grad():
        actual,_=optimized(beta,orient,pose,translation)
        official=model(betas=beta[None].expand(3,-1),global_orient=orient,
                       body_pose=pose,transl=translation).joints[:,:24]
    assert torch.allclose(actual,official,atol=1e-5,rtol=1e-5)
