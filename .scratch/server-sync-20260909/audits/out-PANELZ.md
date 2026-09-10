Delivered [SCORING-PANEL-Z-2026-09-10.md](/home/sat/mcrl-v025-panelz-ws/SCORING-PANEL-Z-2026-09-10.md) and [panel-q1v2z.json](/home/sat/mcrl-v025-panelz-ws/artifacts/panel-q1v2z.json).

- Widths: C1/C2/C3 = `30/44/296`; C3 member = `66`
- Panel SHA-256: `2a905423c8b9b573bef56398ad4b36ce671cc1a41bf232df07d359e81b69e203`
- Real z checkpoint: seed `5166716249291843642`, epoch `100`
- Real scorer: exit `0`; F6/F7/F8 rows `9/5/5`
- Scorer peak RSS: `735,141,888` bytes
- Maximum build RSS: `2,052,612,096` bytes
- Structural verification: all 20 anchors and 19,780 catalogue profiles/outcomes unchanged
- `synthetic_smoke_not_evidence`: `false`; no fixture physical/state value survives
- No EE value or route claim is reported

The shared physical content is reusable across schemas, but the current strict scorer requires one panel file per schema. A future schema revision could instead store one physical core with schema-keyed state blocks.
