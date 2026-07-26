"""
Shared OBJ mesh I/O for the rvectr backend.

`load_smpl_faces` was previously copy-pasted, byte for byte, into seven scripts;
`write_obj` into seven more under two names (`export_obj`, `export_smpl_obj`),
differing only in the comment line each wrote at the top of the file.

That comment line is why this module exists rather than just deduplicating. The
old headers asserted qualities of the output — "Perfect Anchored", "Upright
Zero-Drift", "Muscular" — while saying nothing about where the geometry came
from. A stray .obj on disk was therefore indistinguishable between a mesh
recovered from video and one generated from hand-authored joint angles, which is
exactly the confusion that produced this project's worst defect. Every mesh
written through here now records its own provenance instead.
"""

import os


def load_smpl_faces(ref_obj_path):
    """
    Read 1-indexed face indices from an OBJ, ignoring texture/normal fields.

    Returns a list of index lists, suitable for passing straight to write_obj.
    """
    faces = []
    with open(ref_obj_path, "r") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.strip().split()
                # OBJ faces are "f v/vt/vn ..." and 1-indexed; keep the v field.
                face = [int(p.split("/")[0]) for p in parts[1:]]
                faces.append(face)
    return faces


def write_obj(verts, faces, obj_path, source, measured, note=None):
    """
    Write an OBJ with a provenance header.

    Args:
        verts:    (N, 3) vertex positions.
        faces:    list of 1-indexed face index lists.
        obj_path: destination path.
        source:   the script producing this mesh — pass `__file__`.
        measured: True  — geometry derives from recorded video via pose recovery.
                  False — any part of it was authored, scripted, or stylised.
                  None  — this script only transforms an existing mesh sequence
                          (smoothing, anchoring, reorienting, copying), so
                          provenance is whatever the input had. A transform
                          cannot upgrade authored geometry into a measurement,
                          and must not claim to.
        note:     optional one-line qualifier, e.g. "body shape restyled".

    `measured` is mandatory and has no default on purpose: deciding whether an
    artefact is a measurement is the one thing a caller must not do by accident.
    """
    if measured is None:
        origin = "INHERITED (transformed from an existing mesh; check the input's provenance)"
    elif measured:
        origin = "RECOVERED (derived from recorded video)"
    else:
        origin = "SYNTHETIC (authored or stylised — NOT a measurement)"

    with open(obj_path, "w") as f:
        f.write(f"# SMPL body mesh — {len(verts)} vertices, {len(faces)} faces\n")
        f.write(f"# provenance: {origin}\n")
        f.write(f"# written by: {os.path.basename(source)}\n")
        if note:
            f.write(f"# note: {note}\n")
        for v in verts:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for face in faces:
            f.write(f"f {face[0]} {face[1]} {face[2]}\n")
