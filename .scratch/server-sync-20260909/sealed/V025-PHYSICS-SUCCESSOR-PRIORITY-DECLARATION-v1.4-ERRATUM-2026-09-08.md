# V025 priority declaration — v1.4 erratum (controller, sealed before any formal successor outcome; 2026-09-08 ≈ 18:15 UTC)

v1.0–v1.3 are preserved unchanged. This erratum fixes two ambiguities found by pipeline audit C; it changes no design, order or constant.

1. **δ units.** The success margin is a **relative** pooled-EE gain: EE_FULL / EE_DROP − 1 ≥ +0.5 % (the phrase "+0.5 pp" in v1.2 §4 meant this relative percentage; pooled EE has no percentage-point scale). The 95 % lower bound of that relative gain must exceed +0.5 %.
2. **Interval convention.** All bootstrap intervals are central 95 % percentile intervals (2.5th/97.5th percentiles, linear interpolation as implemented by `numpy.quantile` default); the one-sided decision uses the corresponding endpoint (2.5th for gains and availability, 97.5th for handover rate and Φ-priced cost), which is conservative relative to a 5 % one-sided bound and is retained as declared.

Seal: sha256 in the companion `.sha256` file.
