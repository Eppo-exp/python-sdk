from eppo_client.sharders import MD5Sharder, DeterministicSharder


def test_md5_sharder():
    sharder = MD5Sharder()
    inputs = [
        ("test-input", 5619),
        ("alice", 3170),
        ("bob", 7420),
        ("charlie", 7497),
    ]
    total_shards = 10000
    for input, expected_shard in inputs:
        assert sharder.get_shard(input, total_shards) == expected_shard


def test_deterministic_sharder_present():
    lookup = {"test-input": 5}
    sharder = DeterministicSharder(lookup)
    input = "test-input"
    total_shards = 10  # totalShards is ignored in DeterministicSharder
    assert sharder.get_shard(input, total_shards) == 5


def test_deterministic_sharder_absent():
    lookup = {"some-other-input": 7}
    sharder = DeterministicSharder(lookup)
    input = "test-input-not-in-lookup"
    total_shards = 10  # totalShards is ignored in DeterministicSharder
    assert sharder.get_shard(input, total_shards) == 0
