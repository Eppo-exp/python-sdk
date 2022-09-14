import hashlib
import datetime
import logging
from typing import Optional
from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.configuration_requestor import (
    ExperimentConfigurationDto,
    ExperimentConfigurationRequestor,
)
from eppo_client.constants import POLL_INTERVAL_MILLIS, POLL_JITTER_MILLIS
from eppo_client.poller import Poller
from eppo_client.rules import find_matching_rule
from eppo_client.shard import get_shard, is_in_shard_range
from eppo_client.validation import validate_not_blank

logger = logging.getLogger(__name__)


class EppoClient:
    def __init__(
        self,
        config_requestor: ExperimentConfigurationRequestor,
        assignment_logger: AssignmentLogger,
    ):
        self.__config_requestor = config_requestor
        self.__assignment_logger = assignment_logger
        self.__poller = Poller(
            interval_millis=POLL_INTERVAL_MILLIS,
            jitter_millis=POLL_JITTER_MILLIS,
            callback=config_requestor.fetch_and_store_configurations,
        )
        self.__poller.start()

    def get_assignment(
        self, subject_key: str, flag_key: str, subject_attributes=dict()
    ) -> Optional[str]:
        """Maps a subject to a variation for a given experiment
        Returns None if the subject is not part of the experiment sample.

        :param subject_key: an identifier of the experiment subject, for example a user ID.
        :param flag_key: an experiment or feature flag identifier
        :param subject_attributes: optional attributes associated with the subject, for example name and email.
        The subject attributes are used for evaluating any targeting rules tied to the experiment.
        """
        validate_not_blank("subject_key", subject_key)
        validate_not_blank("flag_key", flag_key)
        experiment_config = self.__config_requestor.get_configuration(flag_key)
        override = self._get_subject_variation_override(experiment_config, subject_key)
        if override:
            return override

        if experiment_config is None or not experiment_config.enabled:
            logger.info(
                "[Eppo SDK] No assigned variation. No active experiment or flag for key: "
                + flag_key
            )
            return None

        matched_rule = find_matching_rule(subject_attributes, experiment_config.rules)
        if matched_rule is None:
            logger.info(
                "[Eppo SDK] No assigned variation. Subject attributes do not match targeting rules: {0}".format(
                    subject_attributes
                )
            )
            return None

        allocation = experiment_config.allocations[matched_rule.allocation_key]
        if not self._is_in_experiment_sample(
            subject_key,
            flag_key,
            experiment_config.subject_shards,
            allocation.percent_exposure,
        ):
            logger.info(
                "[Eppo SDK] No assigned variation. Subject is not part of experiment sample population"
            )
            return None

        shard = get_shard(
            "assignment-{}-{}".format(subject_key, flag_key),
            experiment_config.subject_shards,
        )
        assigned_variation = next(
            (
                variation.value
                for variation in allocation.variations
                if is_in_shard_range(shard, variation.shard_range)
            ),
            None,
        )
        assignment_event = {
            "experiment": flag_key,
            "variation": assigned_variation,
            "subject": subject_key,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "subjectAttributes": subject_attributes,
        }
        try:
            self.__assignment_logger.log_assignment(assignment_event)
        except Exception as e:
            logger.error("[Eppo SDK] Error logging assignment event: " + str(e))
        return assigned_variation

    def _shutdown(self):
        """Stops all background processes used by the client
        Do not use the client after calling this method.
        """
        self.__poller.stop()

    def _get_subject_variation_override(
        self, experiment_config: Optional[ExperimentConfigurationDto], subject: str
    ) -> Optional[str]:
        subject_hash = hashlib.md5(subject.encode("utf-8")).hexdigest()
        if (
            experiment_config is not None
            and subject_hash in experiment_config.overrides
        ):
            return experiment_config.overrides[subject_hash]
        return None

    def _is_in_experiment_sample(
        self,
        subject: str,
        experiment_key: str,
        subject_shards: int,
        percent_exposure: float,
    ):
        shard = get_shard(
            "exposure-{}-{}".format(subject, experiment_key),
            subject_shards,
        )
        return shard <= percent_exposure * subject_shards
