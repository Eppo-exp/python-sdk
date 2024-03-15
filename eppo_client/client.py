import datetime
import logging
import json
from typing import Any, Dict, Optional, Union
from typing_extensions import deprecated
from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.configuration_requestor import (
    ExperimentConfigurationRequestor,
)
from eppo_client.constants import POLL_INTERVAL_MILLIS, POLL_JITTER_MILLIS
from eppo_client.models import ValueType
from eppo_client.poller import Poller
from eppo_client.sharding import MD5Sharder
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
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        default=None,
    ) -> Optional[str]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            ValueType.STRING,
            default=default,
        )

    def get_integer_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        default=None,
    ) -> Optional[float]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            ValueType.INTEGER,
            default=default,
        )

    def get_float_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        default=None,
    ) -> Optional[float]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            ValueType.FLOAT,
            default=default,
        )

    @deprecated("get_numeric_assignment is deprecated in favor of get_float_assignment")
    def get_numeric_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        default=None,
    ) -> Optional[float]:
        return self.get_float_assignment(
            subject_key,
            flag_key,
            subject_attributes,
            default=default,
        )

    def get_boolean_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        default=None,
    ) -> Optional[bool]:
        return self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            ValueType.BOOLEAN,
            default=default,
        )

    def get_parsed_json_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        default=None,
    ) -> Optional[Dict[Any, Any]]:
        variation_jsons = self.get_assignment_variation(
            subject_key,
            flag_key,
            subject_attributes,
            ValueType.JSON,
            default=default,
        )
        if variation_jsons:
            return json.loads(variation_jsons)

    @deprecated(
        "get_assignment is deprecated in favor of the typed get_<type>_assignment methods"
    )
    def get_assignment(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        default=None,
    ) -> Optional[str]:
        return self.get_assignment_variation(
            subject_key, flag_key, subject_attributes, default=default
        )

    def get_assignment_variation(
        self,
        subject_key: str,
        flag_key: str,
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
        expected_variation_type: Optional[ValueType] = None,
        default=None,
    ):
        try:
            result = self.get_assignment_detail(
                subject_key, flag_key, subject_attributes
            )
            if not result or not result.variation:
                return default
            assigned_variation = result.variation
            if not check_type_match(
                assigned_variation.value_type, expected_variation_type
            ):
                raise TypeError(
                    "Variation value does not have the correct type. Found: {assigned_variation.value_type} != {expected_variation_type}"
                )
            return assigned_variation.value
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
        subject_attributes: Optional[Dict[str, Union[str, float, int, bool]]] = None,
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
        if not subject_attributes:
            subject_attributes = {}

        flag = self.__config_requestor.get_configuration(flag_key)

        if flag is None or not flag.enabled:
            logger.info(
                "[Eppo SDK] No assigned variation. No active flag for key: " + flag_key
            )
            return None

        result = self.__evaluator.evaluate_flag(flag, subject_key, subject_attributes)

        assignment_event = {
            **result.extra_logging,
            "allocation": result.allocation_key if result else None,
            "experiment": f"{flag_key}-{result.allocation_key}" if result else None,
            "featureFlag": flag_key,
            "variation": result.variation.key if result and result.variation else None,
            "subject": subject_key,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "subjectAttributes": subject_attributes,
        }
        try:
            if result.do_log:
                self.__assignment_logger.log_assignment(assignment_event)
        except Exception as e:
            logger.error("[Eppo SDK] Error logging assignment event: " + str(e))
        return result

    def get_flag_keys(self):
        return self.__config_requestor.get_flag_keys()

    def _shutdown(self):
        """Stops all background processes used by the client
        Do not use the client after calling this method.
        """
        self.__poller.stop()


def check_type_match(value_type, expected_type):
    return (
        expected_type is None
        or value_type == expected_type
        or value_type == expected_type.value
    )
