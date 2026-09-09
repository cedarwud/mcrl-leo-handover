# V0.25 ACM causal correction — before/after SMOKE

Status: `SMOKE_NOT_MATRIX`, TRAIN-only. This is a paired diagnostic on two anchors of quarantined `V025_SMOKE/world/1`; it is not a formal outcome.

The same BASE profiles, realised fading samples, powers and 48-boundary endpoints were evaluated under the old and corrected credit rules. Only ACM credit semantics changed.

| semantics | availability | decoded bits | partial-payload energy (J) | pooled EE (bit/J) |
|---|---:|---:|---:|---:|
| before: genie mode selected from realised SINR | 0.791277 | 240,072,304,316.296 | 12,675.247090 | 18,940,246.499 |
| after: `m_tx` from alpha=.10 wanted-link margin view; realised threshold decode | 0.453138 | 71,728,548,992.593 | 12,675.247090 | 5,658,946.803 |

The correction lowers availability by 0.338138 and pooled EE by 70.122%. Energy is bit-identical because v1.9 computes both predicted and executed power from nominal gains; the quantile changes wanted-link predicted reception and `m_tx`, never power or interferer gain.

Per user-step the engine now emits three distinct objects: `m_target` (nominal rate-target power setpoint), `m_tx` (causally chosen transmitted MODCOD), and `realised_outcome` (threshold, realised SINR and decoded flag). Bit credit is `m_tx.efficiency` only when `realised_sinr >= threshold(m_tx)`; otherwise it is zero.

Immutable evidence: `.tmp/stage4h/acm-before-after.json`, receipt SHA-256 `5fa975a282bfb319933ab01eb31c0430c0af904987d05593b53c3efdfd48e2c9`.
