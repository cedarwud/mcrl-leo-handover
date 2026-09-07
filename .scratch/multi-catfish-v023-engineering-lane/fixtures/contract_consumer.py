import numpy as np

SCHEMA = "consumer-schema-v2"
STATUS = "STALE"
CLAIM_CEILING = "CONSUMER_CLAIM"
MODES = ("other",)
ROUTES = ("C9",)
TARGET_UNIT = "unit-b"
ARRAY_LAYOUT = "action-major"
OPS3_SAMPLES_PER_STEP = 48
HORIZON = 4


def read_artifact(path, receipt):
    assert receipt["schema"] == SCHEMA
    receipt.get("consumer_field")
    arrays = np.load(path)
    states = np.asarray(arrays["states"], dtype=np.float64)
    assert states.shape == (3, 2)
    np.asarray(arrays["masks"], dtype=np.int64)
    return states
