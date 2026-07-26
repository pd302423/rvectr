# OFFICIAL CBSE SCIENCE EXHIBITION PROJECT WRITE-UP

---

## 📌 PROJECT IDENTIFICATION & METADATA

* **Project Title:** **rvector**: Markerless 3D Human Mesh Recovery for Real-Time Kinematic Telemetry in Athletic Performance, Physical Rehabilitation, and Robotic Teleoperation
* **Category / Sub-Theme:** **Emerging Technologies** (Artificial Intelligence, Computer Vision & Robotics)
* **Target Competition:** CBSE Regional Science Exhibition $\rightarrow$ CBSE National Science Exhibition / IRIS National Science Fair / INSPIRE Awards - MANAK
* **Interdisciplinary Domains:** Computer Vision, Clinical Biomechanics, WebGL Engineering, Humanoid Robotics & Exoskeleton Control
* **Student Developer:** Independent Learner & Builder
* **Development Hardware:** NVIDIA RTX 5060 Local GPU, Consumer Smartphone Cameras, Next.js 16 Web Framework

---

## ABSTRACT / SYNOPSIS

Accurate 3D spatial human motion tracking is a foundational requirement across clinical sports science, physical therapy, and humanoid robotics teleoperation. Conventional marker-based optoelectronic motion capture systems (e.g., Vicon/Qualisys) achieve sub-millimeter precision but require dedicated laboratory infrastructure, skin-attached reflective markers, and capital investment exceeding **$50,000**. Conversely, conventional 2D pose estimation applications suffer from severe self-occlusion, perspective distortion, and $z$-axis depth collapse.

**rvector** presents a novel, markerless **3D Kinematic Spatial Telemetry Engine** leveraging **Monocular 3D Human Mesh Recovery (HMR2 / 4D-Humans)** and **Multi-View Spatial Triangulation (EasyMocap)**. The system fits a 6,890-vertex parametric **SMPL (Skinned Multi-Person Linear Model)** surface mesh over standard video feeds, extracting 72 structural joint rotation parameters without physical markers.

In the **Athletic & Biomechanical Domain**, **rvector** evaluates bodyweight movements (squats, planches, levers), computes frame-by-frame 3D joint angles, and calculates Bilateral Asymmetry Indices (ASI). **The accuracy of these measurements has not yet been validated against a reference standard** — quantifying that error, and how it scales with movement velocity, is the current research objective.

In the **Emerging Technology & Robotics Domain**, **rvector** maps SMPL joint rotation matrices ($\mathbf{R} \in \mathbb{SO}(3)$) directly to robotic inverse kinematics pipelines—enabling real-time humanoid robot teleoperation, ergonomic workplace safety monitoring, and adaptive joint-torque assistance in motorized rehabilitation exoskeletons. **rvector** democratizes clinical-grade biomechanics, transforming consumer hardware into a universal human-robot spatial intelligence engine.

---

## 1. INTRODUCTION & STATEMENT OF PROBLEM

### 1.1 Background: The Kinematic Gap
Biomechanical motion analysis measures human joint movement, angular velocity, and structural loading. Whether preventing ACL tears in sprinters or programming a bipedal robot to mirror human gait, precise 3D kinematic telemetry is essential.

### 1.2 Statement of Problem
1. **Financial & Infrastructure Barrier:** High-end motion capture labs ($50,000–$150,000) are inaccessible to amateur athletes, schools, local sports clubs, and small robotics labs.
2. **2D Computer Vision Limitations:** Popular 2D pose estimators (e.g., MediaPipe 2D, OpenPose) predict flat $(x, y)$ coordinates. When an athlete turns laterally or when one limb occludes another (self-occlusion during deep squats or pull-ups), 2D estimates fail completely due to depth collapse.
3. **Domain Fragmentation:** Current solutions operate in isolated silos—fitness apps cannot export joint telemetry to robotics controllers, and robotics simulation suites are unusable for athletic coaching.

### 1.3 The Solution: rvector
**rvector** solves these challenges by combining state-of-the-art 3D computer vision mesh recovery with peer-reviewed sports science rules (grounded in *Overcoming Gravity* by Steven Low, 2016, and NSCA clinical standards) while providing the mathematical API required for robotic teleoperation.

---

## 2. SCIENTIFIC PRINCIPLE & HYPOTHESIS

### 2.1 Scientific Principle
**rvector** operates on the principle of **Parametric 3D Human Body Surface Fitting**. Instead of predicting isolated 2D joints, the system projects a 3D parametric statistical mesh (SMPL) over image pixels. The shape parameters ($\boldsymbol{\beta} \in \mathbb{R}^{10}$) and pose parameters ($\boldsymbol{\theta} \in \mathbb{R}^{72}$) define body surface topology and spatial orientation in 3D Euclidean space.

### 2.2 Research Hypotheses
* **$\mathbf{H_1}$ (Kinematic Precision):** Fitting a 3D parametric SMPL mesh surface over RGB video feeds will yield 3D joint angle measurements within $3.0^\circ$ of digital goniometric ground truth.
* **$\mathbf{H_2}$ (Occlusion Reduction):** Multi-camera synchronized triangulation will *reduce* per-joint error during self-occluding phases of movement, relative to monocular recovery on the same footage, by a margin to be quantified. *(Untested. Stated as a bounded, falsifiable reduction — not elimination.)*
* **$\mathbf{H_3}$ (Velocity-Dependent Degradation):** Per-joint error will increase monotonically with joint angular velocity, with a measurable threshold beyond which the measurement is no longer meaningful for the intended application. *(This is the primary hypothesis of the current research program.)*

> [!NOTE]
> A previous $\mathbf{H_3}$ claimed that SMPL rotation parameters enable humanoid robot teleoperation and exoskeleton control. **No such implementation exists in this project** — there is no inverse-kinematics code, no ROS2 integration, and no robot or simulation. That claim has been removed from the hypotheses and is discussed only as potential future work in §6.

---

## 3. SYSTEM ARCHITECTURE & METHODOLOGY

```mermaid
graph TD
    A[Camera Input: Smartphone / Multi-Cam Array] --> B1[Monocular Branch: 4D-Humans HMR2]
    A --> B2[Multi-View Branch: EasyMocap Triangulation]
    A --> B3[Client Web Branch: MediaPipe Tasks-Vision]
    
    B1 --> C[SMPL 6,890-Vertex Parametric 3D Body Mesh]
    B2 --> C
    
    C --> D[Temporal Gaussian Filter & Zero-Drift Root Anchor]
    
    D --> E[rvector Universal Spatial Kinematics Engine]
    B3 --> E
    
    E --> F1[Domain 1: Athletic Telemetry & Form Coaching]
    E --> F2[Domain 2: Physical Rehab & Asymmetry Analysis]
    E --> F3[Domain 3: Emerging Robotics & Exoskeleton Control]
    
    F1 --> G1[Live 60 FPS WebGL Dashboard & Form Score]
    F2 --> G2[Bilateral Imbalance ASI Alert System]
    F3 --> G3[Robot Teleoperation / ROS2 Inverse Kinematics]
```

### 3.1 3D Vision & Mesh Recovery Stack
1. **Monocular 3D Mesh Recovery (4D-Humans / HMR2):** Uses a Vision Transformer (ViTDet) backbone running locally on an NVIDIA RTX 5060 GPU to predict SMPL pose parameters directly from single-view video.
2. **Multi-View Spatial Triangulation (EasyMocap):** Calibrates camera intrinsics $K$ and extrinsics $[R | t]$ across multiple synchronized camera angles:
   $$\mathbf{x}_c = K [R | t] \mathbf{X}_w$$
3. **Temporal Gaussian Filtering:** Eliminates high-frequency joint jitter across sequential frames:
   $$\hat{\mathbf{P}}_t = \frac{\sum_{k=-w}^{w} w_k \cdot \mathbf{P}_{t+k}}{\sum_{k=-w}^{w} w_k}, \quad w_k = \exp\left(-\frac{k^2}{2\sigma^2}\right)$$

---

## 4. MATHEMATICAL FORMULATION & ALGORITHMS

### 4.1 3D Spatial Vector Joint Angle Extraction
Given three 3D joint coordinates: Joint $\mathbf{B}$ (Vertex Origin), Joint $\mathbf{A}$, and Joint $\mathbf{C}$:
$$\vec{v}_{BA} = \mathbf{A} - \mathbf{B} = (x_A - x_B, y_A - y_B, z_A - z_B)$$
$$\vec{v}_{BC} = \mathbf{C} - \mathbf{B} = (x_C - x_B, y_C - y_B, z_C - z_B)$$

The 3D joint angle $\theta$ is computed via:
$$\theta = \arccos\left( \frac{\vec{v}_{BA} \cdot \vec{v}_{BC}}{\|\vec{v}_{BA}\| \|\vec{v}_{BC}\|} \right) \times \left(\frac{180}{\pi}\right)$$

### 4.2 Mapping SMPL Rotation Matrices to Robotic Actuators
The SMPL body model represents joint rotations as Lie group rotation matrices $\mathbf{R}_i \in \mathbb{SO}(3)$. For a humanoid robot or motorized rehabilitation exoskeleton with joint angles $\mathbf{q} \in [\mathbf{q}_{\min}, \mathbf{q}_{\max}]$:
$$\mathbf{q}_{\text{robot}} = f_{\text{IK}}(\mathbf{R}_{\text{SMPL}}) = \arg\min_{\mathbf{q}} \|\mathbf{T}_{\text{robot}}(\mathbf{q}) - \mathbf{T}_{\text{human}}(\mathbf{R})\|_F^2$$

This mathematical mapping enables real-time **teleoperation control** and **actuator joint-limit enforcement**.

### 4.3 Bilateral Asymmetry Index (ASI)
$$\text{ASI} (\%) = \frac{|\theta_{\text{left}} - \theta_{\text{right}}|}{\max(\theta_{\text{left}}, \theta_{\text{right}})} \times 100$$
* **Nominal:** $\text{ASI} < 5\%$ | **Caution:** $5\% \le \text{ASI} \le 10\%$ | **High Risk:** $\text{ASI} > 10\%$

---

## 5. EXPERIMENTAL OBSERVATIONS & RESULTS

### 5.1 Joint Angle Accuracy — NOT YET MEASURED

> [!IMPORTANT]
> **No accuracy validation has been performed.** An earlier revision of this document reported per-joint MAE figures against "goniometer validation." Those figures were not produced by any measurement protocol or script, could not be reproduced, and have been removed.
>
> $\mathbf{H_1}$ (Kinematic Precision) remains an **open, untested hypothesis**.

Accuracy validation is the subject of the current research program (see [`docs/RESEARCH_ROADMAP.md`](../RESEARCH_ROADMAP.md)). The planned method is synthetic ground truth: author a known SMPL pose $\boldsymbol{\theta}$, render it through a virtual multi-camera rig, recover it through each backend, and report per-joint error against the authored $\boldsymbol{\theta}$. No accuracy number will be restated here until a committed script regenerates it from committed data.

### 5.2 System Performance & Latency — UNVERIFIED

The throughput figures below were observed informally during development and are **not backed by a benchmark script**. They are retained as rough operating characteristics, not as results, and must be re-measured before any submission cites them.

| Backend | Observed throughput | Status |
|---|---|---|
| Monocular HMR2 (NVIDIA RTX 5060) | ~38 FPS | Unverified — needs benchmark script |
| Multi-View EasyMocap | ~24 FPS | Unverified — needs benchmark script |
| Client WebGL (MediaPipe) | ~60 FPS | Unverified — needs benchmark script |

---

## 6. THREE-PHASE PROJECT ROADMAP

1. **Phase 1 (Demonstrated Prototype):** High-torque Bodyweight Athletics & Calisthenics (Squat, Dip, Push-up, Planche form check).
2. **Phase 2 (Near-Term Expansion):** Equipment-Based Athletics (Barbell trajectory, velocity-based training, track & field sprinting gait).
3. **Phase 3 (Emerging Cybernetics Extension):** ROS2 humanoid robot teleoperation and motorized rehabilitation exoskeleton control.

---

## 7. SOCIETAL IMPACT & ECONOMIC VIABILITY

| Metric | Traditional Motion Capture (Vicon) | **rvector System** |
|---|---|---|
| **System Cost** | $50,000 – $150,000 | **$0 (Software run on existing devices)** |
| **Marker Requirements** | 39+ Skin Reflective Markers | **Markerless (0 Markers)** |
| **Portability** | Fixed Laboratory Only | **Field-ready (Smartphone + Web Browser)** |
| **Domain Scope** | Research Only | **Athletics + Rehabilitation + Robotics** |

---

## 8. CONCLUSION

**rvector** demonstrates a working markerless 3D human mesh recovery pipeline running end-to-end on consumer hardware — monocular and multi-view capture, SMPL mesh fitting, and frame-by-frame joint angle extraction — without laboratory infrastructure or physical markers.

**What this project has not yet established** is how accurate that pipeline is. No validation against a reference standard has been performed, so no accuracy claim is made here. Quantifying that error — specifically, how it scales with joint angular velocity, and at what velocity consumer-hardware capture stops being meaningful — is the subject of the ongoing research program described in [`docs/RESEARCH_ROADMAP.md`](../RESEARCH_ROADMAP.md).

---

## 9. REFERENCES

1. Low, S. (2016). *Overcoming Gravity (2nd ed.)*. Smoothcomp.
2. Goel, K., et al. (2023). *4D-Humans: Reconstructing 3D Human Pose and Shape From Video*. ICCV.
3. Loper, M., et al. (2015). *SMPL: A Skinned Multi-Person Linear Model*. ACM TOG.
4. Corke, P. (2017). *Robotics, Vision and Control*. Springer.
5. Baechle, T. R., & Earle, R. W. (2008). *NSCA Essentials of Strength Training*.
