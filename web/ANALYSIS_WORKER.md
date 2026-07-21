# rvector analysis worker contract

The web app creates one `analysis_jobs` row per uploaded assessment video. A worker should claim `queued` rows, update its own status to `processing`, download the private `assessment-videos/<video_path>` object, then post the final response to the web app.

## Required environment

```text
SUPABASE_SERVICE_ROLE_KEY=<server-only Supabase service role key>
ANALYSIS_CALLBACK_SECRET=<long random shared secret>
```

Set both in the web deployment and give the worker the same callback secret. Do not expose either in browser code.

## Callback

`POST /api/analysis/callback`

```http
Authorization: Bearer <ANALYSIS_CALLBACK_SECRET>
Content-Type: application/json
```

```json
{
  "job_id": "uuid",
  "status": "complete",
  "score": 84.5,
  "rep_count": 10,
  "summary": "Depth was consistent; mild asymmetry appeared late in the set.",
  "faults": ["left_right_asymmetry"],
  "metrics": {
    "min_knee_angle": 88,
    "average_torso_lean": 32,
    "knee_symmetry_delta": 6
  },
  "evidence_paths": ["<user_id>/evidence/<job_id>-bottom.jpg"],
  "model_version": "mediapipe-squat-rules/v1"
}
```

Use `status: "failed"` with `error_message` for a terminal processing error. The database updates the associated workout to `completed` when all its jobs reach a terminal state.
