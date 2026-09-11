#!/usr/bin/env python3
"""SPECPROFILE part 2: the DECLARED-RULE class at C=50 (erratum 23).

Profiles all nine declared C=50 rules from BEAMCOUNT, and the strongest of them
(S2_descending_coverage | A2_max_nominal_gain, 52.042303 Mbit/J pooled full-48),
against the same declared QoS guard as part 1.

DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM.  Learner-free.  Same evaluator discipline:
one fresh dense boundary-0 StepEvaluator per anchor with BASE and the incumbent
in the first evaluate_many batch; one separate fresh realised full-48
StepEvaluator per anchor populated by exactly one evaluate_many call; scalar
StepEvaluator.evaluate replaced by a raising stub and asserted zero.
"""

from __future__ import annotations

import gc
import json
import math
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, '/home/sat/mcrl-v025-specprofile-ws/.scratch/specprofile')
import run_specprofile as sp  # noqa: E402

DECLARED_LABELS = [
    'CAP_050__S1_ascending_coverage|A1_coverage_first',
    'CAP_050__S1_ascending_coverage|A2_max_nominal_gain',
    'CAP_050__S1_ascending_coverage|A3_least_loaded',
    'CAP_050__S2_descending_coverage|A1_coverage_first',
    'CAP_050__S2_descending_coverage|A2_max_nominal_gain',
    'CAP_050__S2_descending_coverage|A3_least_loaded',
    'CAP_050__S3_descending_nominal_gain|A1_coverage_first',
    'CAP_050__S3_descending_nominal_gain|A2_max_nominal_gain',
    'CAP_050__S3_descending_nominal_gain|A3_least_loaded',
]
BEST_DECLARED = 'CAP_050__S2_descending_coverage|A2_max_nominal_gain'
OUTPUT = sp.OUTDIR / 'specprofile-declared-rules.json'
PARTIAL = sp.OUTDIR / 'specprofile-declared-rules-partial.json'


def load_declared():
    arms = {}
    digests = {}
    for carrier in sp.CARRIERS:
        path = sp.BEAMCOUNT / f'beamcount-shard-{carrier}.json'
        digests[carrier] = sp.sha256_file(path)
        shard = json.loads(path.read_text(encoding='utf-8'))
        for anchor in shard['anchors']:
            row = {}
            for label in DECLARED_LABELS:
                endpoint = anchor['endpoints'][label]
                row[label] = {
                    'mapping': sp.parse_configuration_id(endpoint['configuration_id']),
                    'recorded_ee_bit_per_j': endpoint['ee_bit_per_j'],
                    'recorded_served_phy': endpoint['served_phy'],
                    'recorded_rate_target_attained': endpoint['rate_target_attained'],
                }
            arms[anchor['anchor_id']] = row
    return arms, digests


def main() -> int:
    sp.check_runtime()
    started = time.perf_counter()
    sp.OUTDIR.mkdir(parents=True, exist_ok=True)
    declared, digests = load_declared()
    pilot = sp.load_pilot()
    runner = pilot.ENGINE
    from mcrl.physics_v025.targets import classify_physical_transition
    run_setting = runner.run_setting_for('a-r0')
    sp.forbid_scalar_evaluate(runner)
    from mcrl.physics_v025.provider_legacy import LegacyWorldProvider
    from mcrl.physics_v025.tapes import build_world_tape

    t0 = time.perf_counter()
    tape = build_world_tape(domain=pilot.TRAIN_WORLDS[0],
                            provider=LegacyWorldProvider(role='pilot-source'),
                            steps=33, start_time_s=0.0)
    tape_seconds = time.perf_counter() - t0
    sp.check_runtime()
    print(f'peak RSS {sp.peak_rss_bytes()/2**30:.3f} GiB after tape ({tape_seconds:.1f}s)', flush=True)

    panel = [(s, c) for s in range(4) for c in sp.CARRIERS]
    payload = {
        'schema': 'mcrl-v025-specialist-qos-profile-declared-rules-v1',
        'status': 'RUNNING',
        'claim_status': 'DESIGN_PHASE_MEASUREMENT_NOT_A_CLAIM',
        'learner_free': True,
        'erratum': 'V025-CONTROLLER-ERRATUM-23: CAP_050 is a search winner, not a declared rule',
        'declared_rule_labels': DECLARED_LABELS,
        'best_declared_rule': BEST_DECLARED,
        'panel': {'domain': tape.domain, 'world_tape_digest': tape.digest,
                  'evaluation_boundaries': list(range(48))},
        'declared_prices': {'phi_1_same_satellite_beam_change_kappa': sp.PHI_SAME_SATELLITE,
                            'phi_2_satellite_change_kappa': sp.PHI_SATELLITE_CHANGE,
                            'decision_interval_s': sp.DECISION_INTERVAL_S,
                            'budget_slack': sp.BUDGET_SLACK},
        'source': {'beamcount_shard_sha256': digests,
                   'pilot_sha256': sp.sha256_file(sp.PILOT_PATH),
                   'engine_sha256': sp.sha256_file(sp.ENGINE_PATH)},
        'runtime': {'python': sys.executable,
                    'niceness': os.getpriority(os.PRIO_PROCESS, 0),
                    'thread_pins': {n: os.environ[n] for n in sp.THREAD_VARS},
                    'world_tape_seconds': tape_seconds},
        'anchors': [],
    }
    sp.atomic_write(PARTIAL, payload)

    anchor_rows = []
    for position, (step_index, carrier) in enumerate(panel, 1):
        anchor_id = f'{tape.domain}|{step_index}|{carrier}'
        anchor_started = time.perf_counter()
        options, _census = runner._legal_options(tape, step_index)
        arrays = tape.steps[step_index].arrays
        row_of = arrays._row_index()

        def gain_of(user, beam, _a=arrays, _r=row_of):
            return float(_a.nominal_gain[0, _r[(user, beam)]])

        base = runner._base_configuration(tape, step_index, carrier)
        incumbent = runner._base_configuration(tape, max(0, step_index - 1), carrier)
        rekeyed = runner._rekeyed_users(tape, step_index)
        users = sorted(options)
        inc_map = dict(incumbent.mapping)
        base_map = dict(base.mapping)

        held_map = {}
        for user in users:
            identity = inc_map.get(user)
            held_map[user] = identity if (identity is not None and identity in options[user]) else None

        rule_map = dict(declared[anchor_id][BEST_DECLARED]['mapping'])

        # constrained arm 1: same declared assignment rule (A2 max nominal gain)
        # restricted to legal options on the incumbent satellite
        satlock_map = {}
        satlock_exempt = []
        for user in users:
            identity = inc_map.get(user)
            same = [] if identity is None else [b for b in options[user] if b[0] == identity[0]]
            if not same:
                satlock_map[user] = rule_map.get(user)
                satlock_exempt.append(user)
            else:
                satlock_map[user] = min(same, key=lambda b: (-gain_of(user, b), b))

        # constrained arm 2/3: zero handover, and a per-anchor handover/Phi budget
        base_events = sp.event_ledger(inc_map, base_map, rekeyed, classify_physical_transition)
        base_qos = sp.qos_from_events(base_events, len(users))
        count_budget = math.floor(sp.BUDGET_SLACK * base_qos['handover_events'])
        phi_budget = sp.BUDGET_SLACK * base_qos['phi_priced_handover_cost_kappa']

        search = sp.Boundary0(runner, tape, step_index, incumbent, run_setting, base,
                              f'specprofile2-s{step_index}')
        held_cfg = search.make(held_map)
        rule_cfg = search.make(rule_map)
        search.submit([base, held_cfg, rule_cfg])
        held_profile = search.read(held_cfg)
        if held_profile is None:
            raise RuntimeError(f'held configuration invalid at {anchor_id}')
        held_ee, _held_served = sp.Boundary0.score(held_profile)

        priced = []
        for user in users:
            target = rule_map.get(user)
            if target == held_map.get(user) or inc_map.get(user) is None or target is None:
                continue
            priced.append(user)
        trials = []
        for user in priced:
            trial = dict(held_map)
            trial[user] = rule_map[user]
            trials.append((user, search.make(trial)))
        search.submit([cfg for _u, cfg in trials])
        ranked = []
        for user, cfg in trials:
            profile = search.read(cfg)
            if profile is None:
                continue
            ee, _served = sp.Boundary0.score(profile)
            ranked.append((ee - held_ee, user))
        ranked.sort(key=lambda r: (-r[0], r[1]))
        budget_map = dict(held_map)
        used_count = 0
        used_phi = 0.0
        for _delta, user in ranked:
            before_id = inc_map[user]
            after_id = rule_map[user]
            price = (sp.PHI_SATELLITE_CHANGE if before_id[0] != after_id[0]
                     else sp.PHI_SAME_SATELLITE)
            if used_count + 1 > count_budget or used_phi + price > phi_budget + 1e-12:
                continue
            budget_map[user] = after_id
            used_count += 1
            used_phi += price
        b0_submitted = search.submitted
        search.close()
        sp.check_runtime()

        arms = {'BASE': base_map, 'INCUMBENT_HELD': held_map}
        for label in DECLARED_LABELS:
            arms[label] = dict(declared[anchor_id][label]['mapping'])
        arms['BEST_DECLARED_RULE'] = rule_map
        arms['BEST_DECLARED_RULE_SAT_LOCK'] = satlock_map
        arms['BEST_DECLARED_RULE_ZERO_HANDOVER'] = dict(held_map)
        arms['BEST_DECLARED_RULE_BUDGET_VS_BASE'] = budget_map

        endpoint_eval = runner.StepEvaluator(
            tape, runner._setting('a-r0'), step_index,
            transition_from=incumbent, cell_rekeyed_users=rekeyed,
            field='realised', counter=runner.EvaluationCounter(),
            run_setting=run_setting, boundary_indices=tuple(range(48)))
        configs = {label: runner._configuration(base, mapping, kind='specprofile2')
                   for label, mapping in arms.items()}
        endpoint_eval.evaluate_many(list(configs.values()))
        rows = {}
        for label, mapping in arms.items():
            cfg = configs[label]
            if cfg.configuration_id in endpoint_eval._invalid:
                rows[label] = {'invalid': True}
                continue
            profile = endpoint_eval._evaluated[cfg.configuration_id]
            metrics = sp.endpoint_metrics(profile, mapping)
            events = sp.event_ledger(inc_map, mapping, rekeyed, classify_physical_transition)
            metrics['qos'] = sp.qos_from_events(events, len(users))
            rows[label] = metrics
        del endpoint_eval
        gc.collect()

        anchor_rows.append({
            'anchor_id': anchor_id, 'anchor_index': position,
            'step_index': step_index, 'carrier': carrier,
            'roster_users': len(users),
            'incumbent_is_same_step_base': step_index == 0,
            'recorded': {label: {k: v for k, v in row.items() if k != 'mapping'}
                         for label, row in declared[anchor_id].items()},
            'constrained_construction': {
                'sat_lock_exempt_users': len(satlock_exempt),
                'budget_reference': 'BASE',
                'budget_reference_handovers': base_qos['handover_events'],
                'budget_reference_phi_kappa': base_qos['phi_priced_handover_cost_kappa'],
                'budget_count_cap': count_budget,
                'budget_phi_cap_kappa': phi_budget,
                'budget_admitted_users': used_count,
                'budget_used_phi_kappa': used_phi,
                'priced_candidate_moves': len(priced),
            },
            'boundary0_configurations_submitted': b0_submitted,
            'arms': rows,
            'anchor_seconds': time.perf_counter() - anchor_started,
            'peak_rss_bytes': sp.peak_rss_bytes(),
        })
        payload['anchors'] = anchor_rows
        sp.atomic_write(PARTIAL, payload)
        print(f'anchor {position}/12 {anchor_id} '
              f'{anchor_rows[-1]["anchor_seconds"]:.1f}s '
              f'rule_ee={rows["BEST_DECLARED_RULE"]["ee_bit_per_j"]/1e6:.6f} '
              f'ho={rows["BEST_DECLARED_RULE"]["qos"]["handover_events"]} '
              f'rss={sp.peak_rss_bytes()/2**30:.2f}GiB', flush=True)
        sp.check_runtime()

    payload['anchors'] = anchor_rows
    payload['scalar_evaluate_calls'] = sp.SCALAR_EVALUATE_CALLS
    payload['scalar_evaluate_assertion'] = 'PASS' if sp.SCALAR_EVALUATE_CALLS == 0 else 'FAIL'
    payload['status'] = 'COMPLETE'
    payload['runtime']['wall_seconds'] = time.perf_counter() - started
    payload['runtime']['peak_rss_bytes'] = sp.peak_rss_bytes()
    payload['runner_sha256'] = sp.sha256_file(Path(__file__))
    assert sp.SCALAR_EVALUATE_CALLS == 0, 'scalar StepEvaluator.evaluate was called'
    print('PASS: zero scalar StepEvaluator.evaluate calls', flush=True)
    sp.atomic_write(OUTPUT, payload)
    print(f'wrote {OUTPUT}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
