from eppo_client.configuration_requestor import (
    AllocationDto,
    ExperimentConfigurationDto,
)
from eppo_client.configuration_store import ConfigurationStore

test_exp = ExperimentConfigurationDto(
    subject_shards=1000,
    enabled=True,
    name="randomization_algo",
    allocations={"allocation-1": AllocationDto(percent_exposure=1, variations=[])},
)

TEST_MAX_SIZE = 10

store: ConfigurationStore[ExperimentConfigurationDto] = ConfigurationStore(
    max_size=TEST_MAX_SIZE
)


def test_get_configuration_unknown_key():
    store.set_configurations({"randomization_algo": test_exp})
    assert store.get_configuration("unknown_exp") is None


def test_get_configuration_known_key():
    store.set_configurations({"randomization_algo": test_exp})
    assert store.get_configuration("randomization_algo") == test_exp


def test_evicts_old_entries_when_max_size_exceeded():
    store.set_configurations({"item_to_be_evicted": test_exp})
    assert store.get_configuration("item_to_be_evicted") == test_exp
    configs = {}
    for i in range(0, TEST_MAX_SIZE):
        configs["test-entry-{}".format(i)] = test_exp
    store.set_configurations(configs)
    assert store.get_configuration("item_to_be_evicted") is None
    assert (
        store.get_configuration("test-entry-{}".format(TEST_MAX_SIZE - 1)) == test_exp
    )
