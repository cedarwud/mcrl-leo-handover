import numpy as np

SCHEMA = "producer-schema-v1"
STATUS = "READY"
CLAIM_CEILING = "PRODUCER_CLAIM"
MODES = ("informed", "neutral")
ROUTES = ("C1", "C2")
TARGET_UNIT = "unit-a"
ARRAY_LAYOUT = "feature-major"
OPS3_SAMPLES_PER_STEP = 47
HORIZON = 3


def write_artifact(path, values):
    receipt = {
        "schema": SCHEMA,
        "status": STATUS,
        "claim_ceiling": CLAIM_CEILING,
        "mode": MODES[0],
        "route": ROUTES[0],
        "target_unit": TARGET_UNIT,
        "producer_field": True,
    }
    states = np.asarray(values, dtype=np.float32).reshape(2, 3)
    np.savez(path, states=states, mask=np.asarray([True], dtype=np.bool_))
    return receipt


def read_own_artifact(path, receipt):
    assert receipt["schema"] == SCHEMA
    arrays = np.load(path)
    states = np.asarray(arrays["states"], dtype=np.float32)
    assert states.shape == (2, 3)
    np.asarray(arrays["mask"], dtype=np.bool_)
    return states
