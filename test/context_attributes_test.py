from eppo_client.bandit import ContextAttributes


def test_from_dict_treats_bools_as_categorical():
    attrs = ContextAttributes.from_dict(
        {
            "categorical": True,
        }
    )

    assert attrs.categorical_attributes == {
        "categorical": "true",
    }
    assert attrs.numeric_attributes == {}
