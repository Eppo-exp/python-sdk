from eppo_client.configuration_requestor import ExperimentConfigurationDto
from eppo_client.configuration_store import ConfigurationStore

test_exp = ExperimentConfigurationDto(
    subject_shards=1000,
    percent_exposure=1,
    enabled=True,
    variations=[],
    name="randomization_algo",
)

store: ConfigurationStore[ExperimentConfigurationDto] = ConfigurationStore(
    ttl_seconds=100, max_size=1
)
store.set_configurations({"randomization_algo": test_exp})


def test_get_configuration_unknown_key():
    assert store.get_configuration("unknown_exp") is None


def test_get_configuration_known_key():
    assert store.get_configuration("randomization_algo") == test_exp
