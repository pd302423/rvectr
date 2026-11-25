"""Model-free tests of correspondence, arbitrary orientation and missing-data contracts."""
import numpy as np
import pytest
from rvectr.fitting import (COCO_TO_SMPL, classify_frames, rigid_alignment,
                            validate_inputs, FRAME_ESTIMATED, FRAME_UNAVAILABLE)


def test_face_landmarks_are_not_fabricated_anatomical_targets():
    assert not (set(range(5)) & set(COCO_TO_SMPL))
    assert set(COCO_TO_SMPL.values()) == {1,2,4,5,7,8,16,17,18,19,20,21}


def test_rigid_orientation_supports_horizontal_body_without_free_scale():
    source=np.array([[-.2,0,0],[.2,0,0],[-.3,.5,0],[.3,.5,0]])
    expected=np.array([[0,-1,0],[1,0,0],[0,0,1.]])
    target=source@expected.T+np.array([1.,2.,3.])
    rotation,translation=rigid_alignment(source,target,np.ones(4))
    assert np.allclose(rotation,expected)
    assert np.isclose(np.linalg.det(rotation),1)
    assert np.allclose(source@rotation.T+translation,target)
    assert np.isclose(np.linalg.norm(target[0]-target[1]),np.linalg.norm(source[0]-source[1]))


@pytest.mark.parametrize('timestamps',[[0,0],[.1,0],[0,np.nan]])
def test_original_timestamps_must_be_finite_and_increasing(timestamps):
    with pytest.raises(ValueError):
        validate_inputs(np.zeros((2,17,3)),np.ones((2,17)),timestamps)


def test_missing_points_remain_missing_in_observation_mask():
    xyz=np.zeros((2,17,3))
    xyz[0,13]=np.nan
    confidence=np.ones((2,17))
    confidence[1,14]=0
    _,_,_,observed=validate_inputs(xyz,confidence,[0,.1])
    assert not observed[0,13] and not observed[1,14]
    assert np.isnan(xyz[0,13]).all()


def test_only_short_bounded_missing_intervals_are_estimates():
    xyz=np.full((3,17,3),np.nan)
    confidence=np.zeros((3,17))
    points=np.array([[-.3,1,0],[.3,1,0],[-.2,0,0],[.2,0,0],[-.2,-.5,0],[.2,-.5,0]])
    indices=[5,6,11,12,13,14]
    for frame in [0,2]:
        xyz[frame,indices]=points
        confidence[frame,indices]=1
    _,_,t,observed=validate_inputs(xyz,confidence,[0,.1,.2])
    supported,active,status=classify_frames(xyz,observed,t)
    assert supported.tolist()==[True,False,True]
    assert active.all() and status[1]==FRAME_ESTIMATED
    _,active,status=classify_frames(xyz,observed,np.array([0.,.3,.6]))
    assert not active[1] and status[1]==FRAME_UNAVAILABLE
