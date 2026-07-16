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
};

/**
 * Get the elbow joint angle (wrist -> elbow -> shoulder)
 */
export function getElbowAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const shoulder = landmarks[side === "left" ? LANDMARKS.LEFT_SHOULDER : LANDMARKS.RIGHT_SHOULDER];
  const elbow = landmarks[side === "left" ? LANDMARKS.LEFT_ELBOW : LANDMARKS.RIGHT_ELBOW];
  const wrist = landmarks[side === "left" ? LANDMARKS.LEFT_WRIST : LANDMARKS.RIGHT_WRIST];

  if (!shoulder || !elbow || !wrist) return 0;
  return angleBetweenPoints(wrist, elbow, shoulder);
}

/**
 * Get the hip joint angle (shoulder -> hip -> knee)
 */
export function getHipAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const shoulder = landmarks[side === "left" ? LANDMARKS.LEFT_SHOULDER : LANDMARKS.RIGHT_SHOULDER];
  const hip = landmarks[side === "left" ? LANDMARKS.LEFT_HIP : LANDMARKS.RIGHT_HIP];
  const knee = landmarks[side === "left" ? LANDMARKS.LEFT_KNEE : LANDMARKS.RIGHT_KNEE];

  if (!shoulder || !hip || !knee) return 0;
  return angleBetweenPoints(shoulder, hip, knee);
}

/**
 * Get the knee joint angle (hip -> knee -> ankle)
 */
export function getKneeAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const hip = landmarks[side === "left" ? LANDMARKS.LEFT_HIP : LANDMARKS.RIGHT_HIP];
  const knee = landmarks[side === "left" ? LANDMARKS.LEFT_KNEE : LANDMARKS.RIGHT_KNEE];
  const ankle = landmarks[side === "left" ? LANDMARKS.LEFT_ANKLE : LANDMARKS.RIGHT_ANKLE];

  if (!hip || !knee || !ankle) return 0;
  return angleBetweenPoints(hip, knee, ankle);
}

/**
 * Get the shoulder joint angle (elbow -> shoulder -> hip)
 */
export function getShoulderAngle(landmarks: Landmark[], side: "left" | "right"): number {
  const elbow = landmarks[side === "left" ? LANDMARKS.LEFT_ELBOW : LANDMARKS.RIGHT_ELBOW];
  const shoulder = landmarks[side === "left" ? LANDMARKS.LEFT_SHOULDER : LANDMARKS.RIGHT_SHOULDER];
  const hip = landmarks[side === "left" ? LANDMARKS.LEFT_HIP : LANDMARKS.RIGHT_HIP];

  if (!elbow || !shoulder || !hip) return 0;
  return angleBetweenPoints(elbow, shoulder, hip);
}
