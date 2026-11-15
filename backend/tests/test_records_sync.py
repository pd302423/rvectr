import numpy as np
from rvectr.records import allocate_run, write_json
from rvectr.sync import estimate_audio_offset, interpolate_observations
from rvectr.kinematics import bend_angle


def test_run_numbers_never_reuse_failed_or_existing_runs(tmp_path):
    assert allocate_run(tmp_path).name=='V1.1.1'
    assert allocate_run(tmp_path).name=='V1.1.2'
    (tmp_path/'V1.1.9').mkdir()
    assert allocate_run(tmp_path).name=='V1.1.10'


def test_missing_measurements_serialize_as_null(tmp_path):
    target=tmp_path/'report.json'
    write_json(target,{'values':np.array([np.nan,np.inf,3.])})
    assert 'NaN' not in target.read_text() and 'null' in target.read_text()


def test_audio_sign_and_stream_origins():
    sr=16000
    rng=np.random.default_rng(42)
    other=rng.normal(size=sr*5)
    reference=np.concatenate([np.zeros(sr),other,np.zeros(sr)])
    result=estimate_audio_offset(reference,other,sr,.1,.03)
    assert abs(result['offset_s']-1.07)<.003
    assert result['exposure_alignment_verified'] is False


def test_interpolation_does_not_bridge_gaps_or_extrapolate():
    t=np.array([0.,.04,1.])
    xy=np.array([[[0.,0.]],[[4.,4.]],[[100.,100.]]])
    out,score=interpolate_observations(t,xy,np.ones((3,1)),[-.1,.02,.5,1.1])
    assert np.allclose(out[1],[[2,2]])
    assert np.isnan(out[[0,2,3]]).all()


def test_segment_bend_straight_is_zero_invalid_is_missing():
    assert np.isclose(bend_angle(np.array([0,1,0]),np.zeros(3),np.array([0,-1,0])),0)
    assert np.isnan(bend_angle(np.zeros(3),np.zeros(3),np.ones(3)))
