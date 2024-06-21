from eppo_client.models import Flag
from eppo_client.configuration_store import ConfigurationStore
from eppo_client.models import VariationType


TEST_MAX_SIZE = 10

store: ConfigurationStore[str] = ConfigurationStore()
mock_flag = Flag(
    key="mock_flag",
    variation_type=VariationType.STRING,
    enabled=True,
    variations={},
    allocations=[],
    total_shards=10000,
)


def test_get_configuration_unknown_key():
    store.set_configurations({"flag": mock_flag})
    assert store.get_configuration("unknown_exp") is None


def test_get_configuration_known_key():
    store.set_configurations({"flag": mock_flag})
    assert store.get_configuration("flag") == mock_flag


def test_get_keys():
    store.set_configurations({"flag1": mock_flag, "flag2": mock_flag})
    keys = store.get_keys()
    assert "flag1" in keys
    assert "flag2" in keys
    assert len(keys) == 2


def test_get_configurations():
    config = {"flag1": mock_flag, "flag2": mock_flag}
    store.set_configurations(config)
    configurations = store.get_configurations()
    assert configurations == config


def test_evicts_old_entries_when_max_size_exceeded():
    store.set_configurations({"item_to_be_evicted": mock_flag})
    assert store.get_configuration("item_to_be_evicted") == mock_flag
    configs = {}
    for i in range(0, TEST_MAX_SIZE):
        configs["test-entry-{}".format(i)] = mock_flag
    store.set_configurations(configs)
    assert store.get_configuration("item_to_be_evicted") is None
    assert (
        store.get_configuration("test-entry-{}".format(TEST_MAX_SIZE - 1)) == mock_flag
    )


def test_evicts_old_entries_when_setting_new_flags():
    store: ConfigurationStore[str] = ConfigurationStore()

    store.set_configurations({"flag": mock_flag, "second_flag": mock_flag})
    assert store.get_configuration("flag") == mock_flag
    assert store.get_configuration("second_flag") == mock_flag

    # Updating the flags should evict flags that no longer exist
    store.set_configurations({"flag": mock_flag})
    assert store.get_configuration("flag") == mock_flag
    assert store.get_configuration("second_flag") is None
