import numpy as np
from extract_kinematics import calculate_angle

def test_calculate_angle_90():
    a = np.array([1, 0, 0])
    b = np.array([0, 0, 0])
    c = np.array([0, 1, 0])
    assert np.isclose(calculate_angle(a, b, c), 90.0)

def test_calculate_angle_180():
    a = np.array([-1, 0, 0])
    b = np.array([0, 0, 0])
    c = np.array([1, 0, 0])
    assert np.isclose(calculate_angle(a, b, c), 180.0)

def test_calculate_angle_0():
    a = np.array([1, 0, 0])
    b = np.array([0, 0, 0])
    c = np.array([2, 0, 0])
    assert np.isclose(calculate_angle(a, b, c), 0.0)

def test_calculate_angle_60():
    # Equilateral triangle
    a = np.array([1, 0, 0])
    b = np.array([0, 0, 0])
    c = np.array([0.5, np.sqrt(3)/2, 0])
    assert np.isclose(calculate_angle(a, b, c), 60.0)

def test_calculate_angle_45():
    a = np.array([1, 0, 0])
    b = np.array([0, 0, 0])
    c = np.array([1, 1, 0])
    assert np.isclose(calculate_angle(a, b, c), 45.0)

def test_calculate_angle_3d():
    a = np.array([1, 1, 1])
    b = np.array([0, 0, 0])
    c = np.array([-1, -1, 1])
    # dot product: -1 -1 + 1 = -1
    # norms: sqrt(3), sqrt(3)
    # cos: -1/3
    expected_angle = np.degrees(np.arccos(-1/3))
    assert np.isclose(calculate_angle(a, b, c), expected_angle)

def test_calculate_angle_zero_length():
    a = np.array([0, 0, 0])
    b = np.array([0, 0, 0])
    c = np.array([1, 0, 0])
    assert calculate_angle(a, b, c) == 0.0

def test_calculate_angle_numerical_stability():
    a = np.array([1.00000001, 0, 0])
    b = np.array([1.0, 0, 0])
    c = np.array([1.00000002, 0, 0])
    # Points very close together forming a straight line
    angle = calculate_angle(a, b, c)
    assert np.isclose(angle, 0.0) or np.isclose(angle, 180.0)
