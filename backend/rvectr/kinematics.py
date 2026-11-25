"""Geometric segment angles, not clinical joint-coordinate-system rotations."""
import numpy as np

JOINT_NAMES = ['nose','left_eye','right_eye','left_ear','right_ear','left_shoulder','right_shoulder',
               'left_elbow','right_elbow','left_wrist','right_wrist','left_hip','right_hip',
               'left_knee','right_knee','left_ankle','right_ankle']
ANGLE_TRIPLES = {'left_knee_bend': (11,13,15), 'right_knee_bend': (12,14,16),
                 'left_elbow_bend': (5,7,9), 'right_elbow_bend': (6,8,10)}


def bend_angle(a,b,c):
    u,v = np.asarray(a)-b,np.asarray(c)-b
    den = np.linalg.norm(u,axis=-1)*np.linalg.norm(v,axis=-1)
    cosine = np.sum(u*v,axis=-1)/np.maximum(den,1e-12)
    return np.where((den>1e-9) & np.isfinite(cosine),180-np.degrees(np.arccos(np.clip(cosine,-1,1))),np.nan)


def extract_angles(xyz,timestamps):
    xyz,t = np.asarray(xyz),np.asarray(timestamps)
    if len(t)!=len(xyz) or np.any(np.diff(t)<=0):
        raise ValueError('One strictly increasing timestamp is required per frame')
    return {'angle_convention': '180 minus hip-knee-ankle or shoulder-elbow-wrist interior angle; straight = 0 degrees',
            'measurement_type': 'estimated 3D segment bend, not clinical Euler angles',
            'timestamps_s':t, 'angles_deg': {name:bend_angle(xyz[:,a],xyz[:,b],xyz[:,c])
                                            for name,(a,b,c) in ANGLE_TRIPLES.items()}}
