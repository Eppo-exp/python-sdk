import hashlib
import datetime
import logging
from typing import Any, Dict, Optional
from numbers import Number
from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.configuration_requestor import (
    ExperimentConfigurationDto,
    ExperimentConfigurationRequestor,
    VariationDto,
)
from eppo_client.constants import POLL_INTERVAL_MILLIS, POLL_JITTER_MILLIS
from eppo_client.poller import Poller
from eppo_client.rules import find_matching_rule
from eppo_client.shard import ShardRange, get_shard, is_in_shard_range
from eppo_client.validation import validate_not_blank
from eppo_client.variation_type import VariationType

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

    def get_string_assignment(
        self, subject_key: str, flag_key: str, subject_attributes=dict()
    ) -> Optional[str]:
        assigned_variation = self.get_assignment_variation(subject_key, flag_key, subject_attributes, VariationType.STRING)
        return assigned_variation.typedValue if assigned_variation is not None else assigned_variation

    def get_numeric_assignment(
        self, subject_key: str, flag_key: str, subject_attributes=dict()
    ) -> Optional[Number]:
        assigned_variation = self.get_assignment_variation(subject_key, flag_key, subject_attributes, VariationType.NUMERIC)
        return assigned_variation.typedValue if assigned_variation is not None else assigned_variation

    def get_boolean_assignment(
        self, subject_key: str, flag_key: str, subject_attributes=dict()
    ) -> Optional[bool]:
        assigned_variation = self.get_assignment_variation(subject_key, flag_key, subject_attributes, VariationType.BOOLEAN)
        return assigned_variation.typedValue if assigned_variation is not None else assigned_variation

    def get_parsed_json_assignment(
        self, subject_key: str, flag_key: str, subject_attributes=dict()
    ) -> Optional[Dict[Any, Any]]:
        assigned_variation = self.get_assignment_variation(subject_key, flag_key, subject_attributes, VariationType.JSON)
        return assigned_variation.typedValue if assigned_variation is not None else assigned_variation

    def get_json_string_assignment(
        self, subject_key: str, flag_key: str, subject_attributes=dict()
    ) -> Optional[str]:
        assigned_variation = self.get_assignment_variation(subject_key, flag_key, subject_attributes, VariationType.JSON)
        return assigned_variation.value if assigned_variation is not None else assigned_variation

    # deprecated in favor of the typed get_<type>_assignment methods
    def get_assignment(
        self, subject_key: str, flag_key: str, subject_attributes=dict()
    ) -> Optional[str]:
         assigned_variation = self.get_assignment_variation(subject_key, flag_key, subject_attributes)
         return assigned_variation.value if assigned_variation is not None else assigned_variation


    def get_assignment_variation(
        self, subject_key: str, flag_key: str, subject_attributes: Any, expected_variation_type: Optional[str] = None
    ) -> Optional[VariationDto]:
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
            if expected_variation_type is not None:
                variation_is_expected_type = VariationType.is_expected_type(override, expected_variation_type)
                if not variation_is_expected_type:
                    return None
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
                variation
                for variation in allocation.variations
                if is_in_shard_range(shard, variation.shard_range)
            ),
            None,
        )

        if expected_variation_type is not None:
            variation_is_expected_type = VariationType.is_expected_type(assigned_variation, expected_variation_type)
            if not variation_is_expected_type:
                return None

        assignment_event = {
            "allocation": matched_rule.allocation_key,
            "experiment": f"{flag_key}-{matched_rule.allocation_key}",
            "featureFlag": flag_key,
            "variation": assigned_variation.value,
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
            override_variation = VariationDto(
                name="override",
                value=experiment_config.overrides[subject_hash],
                typedValue=experiment_config.typedOverrides[subject_hash],
                shardRange=ShardRange(start=0, end=10000),
                )
            return override_variation
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
