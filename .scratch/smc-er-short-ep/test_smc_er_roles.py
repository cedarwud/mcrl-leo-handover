from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("smc_er_roles", HERE / "smc_er_roles.py")
assert SPEC is not None and SPEC.loader is not None
R = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = R
SPEC.loader.exec_module(R)


@dataclass
class Mask:
    mask: np.ndarray


class Table:
    def __init__(self, keys):
        self.mask = np.array([key is not None for key in keys], dtype=bool)
        self.norad_ids = np.array([-1 if key is None else key[0] for key in keys])
        self.cell_ids = np.array([-1 if key is None else key[1] for key in keys])

    def association(self, action):
        from mcrl.env.action_contract import Association

        return Association(int(self.norad_ids[action]), int(self.cell_ids[action]))


class State:
    def __init__(self, quality, beam_loads=None):
        self.channel_quality = np.asarray(quality, dtype=float)
        self.beam_loads = np.asarray(
            np.zeros_like(self.channel_quality)
            if beam_loads is None
            else beam_loads,
            dtype=float,
        )


class Specialist:
    def __init__(self, selections):
        self.rng = np.random.default_rng(4)
        self.selections = list(selections)

    def select_row(self, _state, support, *, epsilon, informed):
        del epsilon, informed
        selected = self.selections.pop(0) if self.selections else support[0]
        return int(selected), 1.0 / len(support)


def test_physical_id_remaps_after_slot_reorder():
    before = Table([(10, 1), (10, 2), None])
    after = Table([(10, 2), None, (10, 1)])
    key = R.physical_key_for_action(before, 0)
    assert key == (10, 1)
    assert R.action_for_physical_key(after, key) == 2


def test_local_snr_source_is_masked_and_tie_deterministic():
    actions, probabilities = R.local_snr_greedy_actions(
        [State([3.0, 9.0, 9.0]), State([1.0, 2.0, 3.0])],
        [Mask(np.array([True, False, True])), Mask(np.zeros(3, dtype=bool))],
    )
    assert actions.tolist() == [2, -1]
    assert probabilities.tolist() == [1.0, 1.0]


def test_c2_continuation_uses_physical_key_not_old_index():
    specialist = Specialist([])
    commitment = R.OptionCommitment(
        focal_user=0, physical_key=(10, 1), remaining=2, opened_step=0
    )
    decision = R.c2_persistence_decision(
        specialist=specialist,
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([0]),
        slot_tables=[Table([(10, 2), (10, 1)])],
        incumbents=[(10, 2)],
        commitment=commitment,
        epsilon=0.0,
        informed=True,
        step_index=1,
    )
    assert decision.actions.tolist() == [1]
    assert decision.trigger == "option_continuation"


def test_c2_opens_only_when_main_proposes_change():
    specialist = Specialist([1])
    commitment = R.OptionCommitment()
    table = Table([(10, 1), (10, 2)])
    decision = R.c2_persistence_decision(
        specialist=specialist,
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([1]),
        slot_tables=[table],
        incumbents=[(10, 1)],
        commitment=commitment,
        epsilon=0.0,
        informed=True,
        step_index=2,
    )
    assert decision.trigger == "main_change_boundary"
    assert commitment.physical_key == (10, 2)
    assert commitment.remaining == 3


def test_c2_no_trigger_has_no_focal_specialist_transition():
    decision = R.c2_persistence_decision(
        specialist=Specialist([]),
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([0]),
        slot_tables=[Table([(10, 1), (10, 2)])],
        incumbents=[(10, 1)],
        commitment=R.OptionCommitment(),
        epsilon=0.0,
        informed=True,
        step_index=0,
    )
    assert decision.trigger == "no_trigger_main_fallback"
    assert decision.focal_user is None
    assert decision.selected_key is None


def test_c2_activation_churn_opens_only_with_two_certified_choices():
    specialist = Specialist([1])
    commitment = R.OptionCommitment()
    table = Table([(10, 1), (10, 2), (10, 3)])
    decision = R.c2_activation_churn_decision(
        specialist=specialist,
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([2]),
        slot_tables=[table],
        certified_supports={0: (0, 1)},
        commitment=commitment,
        epsilon=0.0,
        informed=True,
        step_index=2,
    )
    assert decision.trigger == "activation_churn_certificate_nonempty"
    assert decision.actions.tolist() == [1]
    assert commitment.physical_key == (10, 2)
    assert commitment.remaining == 3


def test_c2_activation_churn_singleton_support_is_not_a_learned_choice():
    decision = R.c2_activation_churn_decision(
        specialist=Specialist([]),
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([1]),
        slot_tables=[Table([(10, 1), (10, 2)])],
        certified_supports={0: (0,)},
        commitment=R.OptionCommitment(),
        epsilon=0.0,
        informed=True,
        step_index=1,
    )
    assert decision.trigger == "empty_activation_churn_certificate_main_fallback"
    assert decision.focal_user is None


def test_c2_activation_churn_continuation_remaps_physical_id():
    commitment = R.OptionCommitment(
        focal_user=0, physical_key=(10, 1), remaining=2, opened_step=0
    )
    decision = R.c2_activation_churn_decision(
        specialist=Specialist([]),
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([0]),
        slot_tables=[Table([(10, 2), (10, 1)])],
        certified_supports={},
        commitment=commitment,
        epsilon=0.0,
        informed=True,
        step_index=1,
    )
    assert decision.trigger == "activation_churn_option_continuation"
    assert decision.actions.tolist() == [1]


def test_strict_c3_support_encodes_exact_load_gap_and_same_satellite():
    table = Table([(10, 1), (10, 2), (10, 3), (11, 2)])
    support = R.strict_load_actions(
        table=table,
        source_key=(10, 1),
        active_keys=[(10, 1), (10, 2), (10, 3), (11, 2)],
        eligible_loads={(10, 1): 5, (10, 2): 3, (10, 3): 4, (11, 2): 1},
    )
    assert support == (1,)


def test_observable_c2_support_avoids_cold_main_destination():
    incumbent = (10, 1)
    warm = (10, 2)
    cold = (11, 1)
    support = R.observable_c2_supports(
        states=[State([0, 0, 0], beam_loads=[2, 1, 0])],
        main_actions=np.array([2]),
        slot_tables=[Table([incumbent, warm, cold])],
        incumbents=[incumbent],
    )
    assert support == {0: (0, 1)}


def test_observable_c2_support_rejects_warm_main_destination():
    incumbent = (10, 1)
    warm = (10, 2)
    support = R.observable_c2_supports(
        states=[State([0, 0], beam_loads=[2, 1])],
        main_actions=np.array([1]),
        slot_tables=[Table([incumbent, warm])],
        incumbents=[incumbent],
    )
    assert support == {}


def test_c2_observable_decision_opens_from_two_choice_support():
    commitment = R.OptionCommitment()
    decision = R.c2_observable_decision(
        specialist=Specialist([1]),
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([2]),
        slot_tables=[Table([(10, 1), (10, 2), (11, 1)])],
        eligible_supports={0: (0, 1)},
        commitment=commitment,
        epsilon=0.0,
        informed=True,
        step_index=1,
    )
    assert decision.trigger == "observable_activation_onset_choice"
    assert decision.actions.tolist() == [1]
    assert commitment.open


def test_observable_c3_support_adds_explicit_defer_without_future_outcome():
    source = (10, 1)
    destination = (10, 2)
    supports = R.observable_c3_supports(
        states=[
            State([0, 0], beam_loads=[3, 1]),
            State([0], beam_loads=[3]),
            State([0], beam_loads=[3]),
            State([0], beam_loads=[1]),
        ],
        main_actions=np.array([0, 0, 0, 0]),
        slot_tables=[
            Table([source, destination]),
            Table([source]),
            Table([source]),
            Table([destination]),
        ],
        incumbents=[source, source, source, destination],
    )
    assert supports == {0: (0, 1)}


def test_observable_c3_support_requires_main_stay_on_source():
    source = (10, 1)
    destination = (10, 2)
    supports = R.observable_c3_supports(
        states=[
            State([0, 0], beam_loads=[3, 1]),
            State([0], beam_loads=[3]),
            State([0], beam_loads=[3]),
            State([0], beam_loads=[1]),
        ],
        main_actions=np.array([1, 0, 0, 0]),
        slot_tables=[
            Table([source, destination]),
            Table([source]),
            Table([source]),
            Table([destination]),
        ],
        incumbents=[source, source, source, destination],
    )
    assert supports == {}


def test_observable_c3_support_rejects_mismatched_user_counts():
    with np.testing.assert_raises_regex(ValueError, "user count"):
        R.observable_c3_supports(
            states=[State([0], beam_loads=[1])],
            main_actions=np.array([0]),
            slot_tables=[],
            incumbents=[(10, 1)],
        )


def test_c2_c3_support_predicates_are_visible_in_canonical_network_state():
    from mcrl.env.step_types import UserState
    from mcrl.runtime.state_encoding import encode_state
    from mcrl.runtime.trainer_spec import TrainerConfig

    users = 4
    incumbent = (10, 1)
    table = Table([incumbent, (10, 2), (10, 3)])
    raw = UserState(
        access_vector=np.array([1.0, 0.0, 0.0]),
        channel_quality=np.array([8.0, 7.0, 6.0]),
        beam_offsets=np.array([0.01, 0.02, 0.03]),
        beam_loads=np.array([3.0, 1.0, 0.0]),
    )
    encoded = encode_state(raw, num_users=users, config=TrainerConfig())
    n = table.mask.size

    assert encoded.shape == (4 * n,)
    assert np.allclose(encoded[:n], raw.access_vector)
    assert int(np.argmax(encoded[:n])) == R.action_for_physical_key(
        table, incumbent
    )
    assert np.allclose(encoded[3 * n : 4 * n], raw.beam_loads / users)

    network_visible = SimpleNamespace(
        beam_loads=encoded[3 * n : 4 * n] * users
    )
    assert R.observable_c2_supports(
        states=[raw],
        main_actions=[2],
        slot_tables=[table],
        incumbents=[incumbent],
    ) == R.observable_c2_supports(
        states=[network_visible],
        main_actions=[2],
        slot_tables=[table],
        incumbents=[incumbent],
    ) == {0: (0, 1)}
    assert R.observable_c3_supports(
        states=[raw],
        main_actions=[0],
        slot_tables=[table],
        incumbents=[incumbent],
    ) == R.observable_c3_supports(
        states=[network_visible],
        main_actions=[0],
        slot_tables=[table],
        incumbents=[incumbent],
    ) == {0: (0, 1)}


def test_c3_opens_only_with_two_certified_choices():
    commitment = R.OptionCommitment()
    decision = R.c3_relocation_decision(
        specialist=Specialist([2]),
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([0]),
        slot_tables=[Table([(10, 1), (10, 2), (10, 3)])],
        eligible_supports={0: (1, 2)},
        commitment=commitment,
        epsilon=0.0,
        informed=True,
        step_index=1,
    )
    assert decision.trigger == "load_support_relocation"
    assert decision.actions.tolist() == [2]
    assert commitment.physical_key == (10, 3)


def test_c3_singleton_support_is_not_a_learned_choice():
    decision = R.c3_relocation_decision(
        specialist=Specialist([]),
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([0]),
        slot_tables=[Table([(10, 1), (10, 2)])],
        eligible_supports={0: (1,)},
        commitment=R.OptionCommitment(),
        epsilon=0.0,
        informed=True,
        step_index=1,
    )
    assert decision.trigger == "empty_load_support_main_fallback"
    assert decision.focal_user is None


def test_c3_defer_choice_routes_a_focal_transition_without_opening_option():
    commitment = R.OptionCommitment()
    decision = R.c3_relocation_decision(
        specialist=Specialist([0]),
        encoded=np.zeros((1, 2), dtype=np.float32),
        main_actions=np.array([0]),
        slot_tables=[Table([(10, 1), (10, 2)])],
        eligible_supports={0: (0, 1)},
        commitment=commitment,
        epsilon=0.0,
        informed=True,
        step_index=1,
    )
    assert decision.trigger == "load_support_defer_to_main"
    assert decision.focal_user == 0
    assert not commitment.open
    assert not decision.option_open_after_selection


def test_option_closes_on_service_failure_and_horizon():
    first = R.OptionCommitment(focal_user=0, physical_key=(1, 2), remaining=3)
    assert R.advance_option_after_execution(first, focal_served=False, done=False) == (
        "realised_service_failure"
    )
    assert not first.open
    second = R.OptionCommitment(focal_user=0, physical_key=(1, 2), remaining=1)
    assert R.advance_option_after_execution(second, focal_served=True, done=False) == (
        "horizon_exhausted"
    )
    assert not second.open


def test_main_behavior_probability_is_marginal_epsilon_greedy():
    class Main:
        def scalarized_q_values(self, _encoded):
            return np.array([[3.0, 1.0], [1.0, 2.0]])

    probabilities = R.epsilon_greedy_probabilities(
        Main(),
        np.zeros((2, 3), dtype=np.float32),
        [Mask(np.ones(2, dtype=bool)), Mask(np.ones(2, dtype=bool))],
        np.array([0, 0]),
        epsilon=0.2,
    )
    assert probabilities.tolist() == [0.9, 0.1]
