from typing import Final

# Five fixed seeds used for repeated stratified cross-validation.
SEEDS: Final[tuple[int, ...]] = (
    27,
    32,
    59,
    # 74,
    # 93,
)

SEED = SEEDS[0]

TEST_SIZE = 0.20
