export interface Landmark {
  x: number;
  y: number;
  z: number;
  visibility?: number;
}

/**
 * Calculates the angle (in degrees) at point B between vector BA and vector BC.
 * Supports both 2D and 3D calculations. If 3D coordinates are available,
 * it uses all three axes for precise spatial measurement.
 */
export function angleBetweenPoints(a: Landmark, b: Landmark, c: Landmark): number {
  const ba = {
    x: a.x - b.x,
    y: a.y - b.y,
    z: a.z - b.z,
  };
  const bc = {
    x: c.x - b.x,
    y: c.y - b.y,
    z: c.z - b.z,
  };

  // Dot product
  const dotProduct = ba.x * bc.x + ba.y * bc.y + ba.z * bc.z;
  
  // Magnitudes
  const magBA = Math.sqrt(ba.x * ba.x + ba.y * ba.y + ba.z * ba.z);
  const magBC = Math.sqrt(bc.x * bc.x + bc.y * bc.y + bc.z * bc.z);

  if (magBA === 0 || magBC === 0) return 0;

  let cosTheta = dotProduct / (magBA * magBC);
  // Clamp to [-1, 1] to prevent NaN from float precision limits
  cosTheta = Math.max(-1, Math.min(1, cosTheta));

  const angleRad = Math.acos(cosTheta);
  return (angleRad * 180) / Math.PI;
}

// Landmark Indices (MediaPipe Pose)
export const LANDMARKS = {
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
  LEFT_HEEL: 29,
  RIGHT_HEEL: 30,
  LEFT_FOOT_INDEX: 31,
  RIGHT_FOOT_INDEX: 32,
};

/**
 * Helper to verify landmark presence and minimum visibility threshold.
 */
function isLandmarkValid(landmark?: Landmark, minVisibility = 0.3): boolean {
  if (!landmark) return false;
  if (landmark.visibility !== undefined && landmark.visibility < minVisibility) return false;
  return true;
}

/**
 * Get the elbow joint angle (wrist -> elbow -> shoulder)
 */
export function getElbowAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const shoulder = landmarks[side === "left" ? LANDMARKS.LEFT_SHOULDER : LANDMARKS.RIGHT_SHOULDER];
  const elbow = landmarks[side === "left" ? LANDMARKS.LEFT_ELBOW : LANDMARKS.RIGHT_ELBOW];
  const wrist = landmarks[side === "left" ? LANDMARKS.LEFT_WRIST : LANDMARKS.RIGHT_WRIST];

  if (!isLandmarkValid(shoulder) || !isLandmarkValid(elbow) || !isLandmarkValid(wrist)) return 0;
  return angleBetweenPoints(wrist, elbow, shoulder);
}

/**
 * Get the hip joint angle (shoulder -> hip -> knee)
 */
export function getHipAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const shoulder = landmarks[side === "left" ? LANDMARKS.LEFT_SHOULDER : LANDMARKS.RIGHT_SHOULDER];
  const hip = landmarks[side === "left" ? LANDMARKS.LEFT_HIP : LANDMARKS.RIGHT_HIP];
  const knee = landmarks[side === "left" ? LANDMARKS.LEFT_KNEE : LANDMARKS.RIGHT_KNEE];

  if (!isLandmarkValid(shoulder) || !isLandmarkValid(hip) || !isLandmarkValid(knee)) return 0;
  return angleBetweenPoints(shoulder, hip, knee);
}

/**
 * Get the knee joint angle (hip -> knee -> ankle)
 */
export function getKneeAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const hip = landmarks[side === "left" ? LANDMARKS.LEFT_HIP : LANDMARKS.RIGHT_HIP];
  const knee = landmarks[side === "left" ? LANDMARKS.LEFT_KNEE : LANDMARKS.RIGHT_KNEE];
  const ankle = landmarks[side === "left" ? LANDMARKS.LEFT_ANKLE : LANDMARKS.RIGHT_ANKLE];

  if (!isLandmarkValid(hip) || !isLandmarkValid(knee) || !isLandmarkValid(ankle)) return 0;
  return angleBetweenPoints(hip, knee, ankle);
}

/**
 * Get the shoulder joint angle (elbow -> shoulder -> hip)
 */
export function getShoulderAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const elbow = landmarks[side === "left" ? LANDMARKS.LEFT_ELBOW : LANDMARKS.RIGHT_ELBOW];
  const shoulder = landmarks[side === "left" ? LANDMARKS.LEFT_SHOULDER : LANDMARKS.RIGHT_SHOULDER];
  const hip = landmarks[side === "left" ? LANDMARKS.LEFT_HIP : LANDMARKS.RIGHT_HIP];

  if (!isLandmarkValid(elbow) || !isLandmarkValid(shoulder) || !isLandmarkValid(hip)) return 0;
  return angleBetweenPoints(elbow, shoulder, hip);
}

/**
 * Get the ankle joint angle (knee -> ankle -> toe)
 */
export function getAnkleAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const knee = landmarks[side === "left" ? LANDMARKS.LEFT_KNEE : LANDMARKS.RIGHT_KNEE];
  const ankle = landmarks[side === "left" ? LANDMARKS.LEFT_ANKLE : LANDMARKS.RIGHT_ANKLE];
  const toe = landmarks[side === "left" ? LANDMARKS.LEFT_FOOT_INDEX : LANDMARKS.RIGHT_FOOT_INDEX];

  if (!isLandmarkValid(knee) || !isLandmarkValid(ankle) || !isLandmarkValid(toe)) return 0;
  return angleBetweenPoints(knee, ankle, toe);
}

/**
 * Calculates normalized heel lift ratio for a given side.
 * A value close to 0 (or negative) indicates heel is firmly on the ground.
 * A value >= 0.35 indicates significant heel rise/lift off the floor.
 */
export function getHeelLiftRatio(landmarks: Landmark[], side: "left" | "right"): number {
  const heel = landmarks[side === "left" ? LANDMARKS.LEFT_HEEL : LANDMARKS.RIGHT_HEEL];
  const toe = landmarks[side === "left" ? LANDMARKS.LEFT_FOOT_INDEX : LANDMARKS.RIGHT_FOOT_INDEX];
  const ankle = landmarks[side === "left" ? LANDMARKS.LEFT_ANKLE : LANDMARKS.RIGHT_ANKLE];
  const knee = landmarks[side === "left" ? LANDMARKS.LEFT_KNEE : LANDMARKS.RIGHT_KNEE];

  if (!heel || !toe) return 0;

  // Confidence check: do not infer heel rise if landmarks are low confidence
  if (
    (heel.visibility !== undefined && heel.visibility < 0.4) ||
    (toe.visibility !== undefined && toe.visibility < 0.4)
  ) {
    return 0;
  }

  // Vertical difference in screen coordinates (screen Y increases downwards)
  // When heel is higher than toe (lifted), toe.y - heel.y > 0
  const verticalDelta = toe.y - heel.y;

  // Estimate reference scale (foot length in 2D or fraction of tibia length)
  const footLen = Math.hypot(toe.x - heel.x, toe.y - heel.y);
  const tibiaLen = knee && ankle ? Math.hypot(ankle.x - knee.x, ankle.y - knee.y) : 0;
  const refScale = footLen > 0.01 ? footLen : tibiaLen * 0.4 > 0.01 ? tibiaLen * 0.4 : 0.1;

  return verticalDelta / refScale;
}
