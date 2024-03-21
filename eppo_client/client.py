import datetime
import logging
import json
from typing import Any, Dict, Optional
from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.configuration_requestor import (
    ExperimentConfigurationRequestor,
)
from eppo_client.constants import POLL_INTERVAL_MILLIS, POLL_JITTER_MILLIS
from eppo_client.models import VariationType
from eppo_client.poller import Poller
from eppo_client.sharding import MD5Sharder
from eppo_client.types import SubjectAttributes
from eppo_client.validation import validate_not_blank
from eppo_client.eval import FlagEvaluation, Evaluator


logger = logging.getLogger(__name__)


class EppoClient:
    def __init__(
        self,
        config_requestor: ExperimentConfigurationRequestor,
        assignment_logger: AssignmentLogger,
        is_graceful_mode: bool = True,
    ):
        self.__config_requestor = config_requestor
        self.__assignment_logger = assignment_logger
        self.__is_graceful_mode = is_graceful_mode
        self.__poller = Poller(
            interval_millis=POLL_INTERVAL_MILLIS,
            jitter_millis=POLL_JITTER_MILLIS,
            callback=config_requestor.fetch_and_store_configurations,
        )
        self.__poller.start()
        self.__evaluator = Evaluator(sharder=MD5Sharder())

    def get_string_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[SubjectAttributes] = None,
        default=None,
    ) -> Optional[str]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            VariationType.STRING,
            default=default,
        )

    def get_integer_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[SubjectAttributes] = None,
        default=None,
    ) -> Optional[float]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            VariationType.INTEGER,
            default=default,
        )

    def get_numeric_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[SubjectAttributes] = None,
        default=None,
    ) -> Optional[float]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            VariationType.NUMERIC,
            default=default,
        )

    def get_boolean_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[SubjectAttributes] = None,
        default=None,
    ) -> Optional[bool]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            VariationType.BOOLEAN,
            default=default,
        )

    def get_parsed_json_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[SubjectAttributes] = None,
        default=None,
    ) -> Optional[Dict[Any, Any]]:
        variation_jsons = self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            VariationType.JSON,
            default=default,
        )
        if variation_jsons is None:
            return None
        return json.loads(variation_jsons)

    def get_assignment_variation(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[SubjectAttributes] = None,
        expected_variation_type: Optional[VariationType] = None,
        default=None,
    ):
        try:
            result = self.get_assignment_detail(
                subject_key, flag_key, subject_attributes, expected_variation_type
            )
            if not result or not result.variation:
                return default
            return result.variation.value
        except ValueError as e:
            # allow ValueError to bubble up as it is a validation error
            raise e
        except Exception as e:
            if self.__is_graceful_mode:
                logger.error("[Eppo SDK] Error getting assignment: " + str(e))
                return default
            raise e

    def get_assignment_detail(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[SubjectAttributes] = None,
        expected_variation_type: Optional[VariationType] = None,
    ) -> Optional[FlagEvaluation]:
        """Maps a subject to a variation for a given experiment
        Returns None if the subject is not part of the experiment sample.

        :param subject_key: an identifier of the experiment subject, for example a user ID.
        :param flag_key: an experiment or feature flag identifier
        :param subject_attributes: optional attributes associated with the subject, for example name and email.
        The subject attributes are used for evaluating any targeting rules tied to the experiment.
        """
        validate_not_blank("subject_key", subject_key)
        validate_not_blank("flag_key", flag_key)
        if subject_attributes is None:
            subject_attributes = {}

        flag = self.__config_requestor.get_configuration(flag_key)

        if flag is None:
            logger.info("[Eppo SDK] No assigned variation. Flag not found: " + flag_key)
            return None

        if not check_type_match(expected_variation_type, flag.variation_type):
            raise TypeError(
                f"Variation value does not have the correct type."
                f" Found: {flag.variation_type} != {expected_variation_type}"
            )

        if not flag.enabled:
            logger.info(
                "[Eppo SDK] No assigned variation. Flag is disabled: " + flag_key
            )
            return None

        result = self.__evaluator.evaluate_flag(flag, subject_key, subject_attributes)

        assignment_event = {
            **(result.extra_logging if result else {}),
            "allocation": result.allocation_key if result else None,
            "experiment": f"{flag_key}-{result.allocation_key}" if result else None,
            "featureFlag": flag_key,
            "variation": result.variation.key if result and result.variation else None,
            "subject": subject_key,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "subjectAttributes": subject_attributes,
        }
        try:
            if result and result.do_log:
                self.__assignment_logger.log_assignment(assignment_event)
        except Exception as e:
            logger.error("[Eppo SDK] Error logging assignment event: " + str(e))
        return result

    def get_flag_keys(self):
        """
        Returns a list of all flag keys that have been initialized.
        This can be useful to debug the initialization process.

        Note that it is generally not a good idea to pre-load all flag configurations.
        """
        return self.__config_requestor.get_flag_keys()

    def _shutdown(self):
        """Stops all background processes used by the client
        Do not use the client after calling this method.
        """
        self.__poller.stop()


def check_type_match(
    expected_type: Optional[VariationType], actual_type: VariationType
):
    return expected_type is None or actual_type == expected_type
