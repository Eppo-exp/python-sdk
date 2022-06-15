import hashlib
from typing import List, Optional
from eppo_client.configuration_requestor import (
    ExperimentConfigurationDto,
    ExperimentConfigurationRequestor,
)
from eppo_client.constants import POLL_INTERVAL_MILLIS, POLL_JITTER_MILLIS
from eppo_client.poller import Poller
from eppo_client.rules import Rule, matches_any_rule
from eppo_client.shard import get_shard, is_in_shard_range
from eppo_client.validation import validate_not_blank


class EppoClient:
    def __init__(self, config_requestor: ExperimentConfigurationRequestor):
        self.__config_requestor = config_requestor
        self.__poller = Poller(
            interval_millis=POLL_INTERVAL_MILLIS,
            jitter_millis=POLL_JITTER_MILLIS,
            callback=config_requestor.fetch_and_store_configurations,
        )
        self.__poller.start()

    def get_assignment(
        self, subject_key: str, experiment_key: str, subject_attributes=dict()
    ) -> Optional[str]:
        """Maps a subject to a variation for a given experiment
        Returns None if the subject is not part of the experiment sample.

        :param subject_key: an identifier of the experiment subject, for example a user ID.
        :param experiment_key: an experiment identifier
        :param subject_attributes: optional attributes associated with the subject, for example name and email.
        The subject attributes are used for evaluating any targeting rules tied to the experiment.
        """
        validate_not_blank("subject_key", subject_key)
        validate_not_blank("experiment_key", experiment_key)
        experiment_config = self.__config_requestor.get_configuration(experiment_key)
        if (
            experiment_config is None
            or not experiment_config.enabled
            or not self._subject_attributes_satisfy_rules(
                subject_attributes, experiment_config.rules
            )
            or not self._is_in_experiment_sample(
                subject_key, experiment_key, experiment_config
            )
        ):
            return None
        override = self._get_subject_variation_override(experiment_config, subject_key)
        if override:
            return override
        shard = get_shard(
            "assignment-{}-{}".format(subject_key, experiment_key),
            experiment_config.subject_shards,
        )
        return next(
            (
                variation.name
                for variation in experiment_config.variations
                if is_in_shard_range(shard, variation.shard_range)
            ),
            None,
        )

    def _subject_attributes_satisfy_rules(
        self, subject_attributes: dict, rules: List[Rule]
    ) -> bool:
        if len(rules) == 0:
            return True
        return matches_any_rule(subject_attributes, rules)

    def _shutdown(self):
        """Stops all background processes used by the client
        Do not use the client after calling this method.
        """
        self.__poller.stop()

    def _get_subject_variation_override(
        self, experiment_config: ExperimentConfigurationDto, subject: str
    ) -> Optional[str]:
        subject_hash = hashlib.md5(subject.encode("utf-8")).hexdigest()
        if subject_hash in experiment_config.overrides:
            return experiment_config.overrides[subject_hash]
        return None

    def _is_in_experiment_sample(
        self,
        subject: str,
        experiment_key: str,
        experiment_config: ExperimentConfigurationDto,
    ):
        shard = get_shard(
            "exposure-{}-{}".format(subject, experiment_key),
            experiment_config.subject_shards,
        )
        return (
            shard
            <= experiment_config.percent_exposure * experiment_config.subject_shards
        )
