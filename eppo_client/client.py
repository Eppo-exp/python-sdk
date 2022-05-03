from typing import Optional
from eppo_client.configuration_requestor import (
    ExperimentConfigurationDto,
    ExperimentConfigurationRequestor,
)
from eppo_client.shard import get_shard, is_in_shard_range
from eppo_client.validation import validate_not_blank


class EppoClient:
    def __init__(self, config_requestor: ExperimentConfigurationRequestor) -> None:
        self.__config_requestor = config_requestor

    def assign(self, subject: str, flag: str) -> Optional[str]:
        """Maps a subject to a variation for a given experiment
        Returns None if the subject is not part of the experiment sample.

        :param subject: an entity ID, e.g. userId
        :param flag: an experiment identifier
        """
        validate_not_blank("subject", subject)
        validate_not_blank("flag", flag)
        experiment_config = self.__config_requestor.get_configuration(flag)
        if (
            experiment_config is None
            or not experiment_config.enabled
            or not self.is_in_experiment_sample(subject, flag, experiment_config)
        ):
            return None
        shard = get_shard(
            "assignment-{}-{}".format(subject, flag), experiment_config.subject_shards
        )
        return next(
            (
                variation.name
                for variation in experiment_config.variations
                if is_in_shard_range(shard, variation.shard_range)
            ),
            None,
        )

    def is_in_experiment_sample(
        self, subject: str, flag: str, experiment_config: ExperimentConfigurationDto
    ):
        shard = get_shard(
            "exposure-{}-{}".format(subject, flag), experiment_config.subject_shards
        )
        return (
            shard
            <= experiment_config.percent_exposure * experiment_config.subject_shards
        )
