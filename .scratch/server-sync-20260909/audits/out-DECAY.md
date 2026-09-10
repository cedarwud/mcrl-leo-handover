Completed the diagnostic and wrote [DECAY-SCHEDULE-2026-09-10.md](/home/sat/mcrl-v025-decay-ws/DECAY-SCHEDULE-2026-09-10.md).

Key result: parity reproduced exactly. First admissible updates were:

- Step `1e-3`: 2,200
- Step `3e-3`: 2,300
- Plateau: 2,800
- Cosine: 3,200
- Inverse-time: `NONE`—objective motion remained 1.946% versus 1%

All admissible schedules pass before 4,000, but none by 500; the earliest requires 4.4× the current update count. Estimated production costs range from 0.28–0.55 CPU-hours depending on schedule.

No EE quantity was computed or used. Maximum peak RSS was 86,028 KiB; runs used one nice-18, single-threaded Python process with unchanged inputs.
