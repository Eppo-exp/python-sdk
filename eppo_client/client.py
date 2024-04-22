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
from eppo_client.sharders import MD5Sharder
from eppo_client.types import SubjectAttributes, ValueType
from eppo_client.validation import validate_not_blank
from eppo_client.eval import FlagEvaluation, Evaluator, none_result
from eppo_client.version import __version__


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
        flag_key: str,
        subject_key: str,
        subject_attributes: SubjectAttributes,
        default: str,
    ) -> str:
        return self.get_assignment_variation(
            flag_key,
            subject_key,
            subject_attributes,
            default,
            VariationType.STRING,
        )

    def get_integer_assignment(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: SubjectAttributes,
        default: int,
    ) -> int:
        return self.get_assignment_variation(
            flag_key,
            subject_key,
            subject_attributes,
            default,
            VariationType.INTEGER,
        )

    def get_numeric_assignment(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: SubjectAttributes,
        default: float,
    ) -> float:
        # convert to float in case we get an int
        return float(
            self.get_assignment_variation(
                flag_key,
                subject_key,
                subject_attributes,
                default,
                VariationType.NUMERIC,
            )
        )

    def get_boolean_assignment(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: SubjectAttributes,
        default: bool,
    ) -> bool:
        return self.get_assignment_variation(
            flag_key,
            subject_key,
            subject_attributes,
            default,
            VariationType.BOOLEAN,
        )

    def get_json_assignment(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: SubjectAttributes,
        default: Dict[Any, Any],
    ) -> Dict[Any, Any]:
        json_value = self.get_assignment_variation(
            flag_key,
            subject_key,
            subject_attributes,
            None,
            VariationType.JSON,
        )
        if json_value is None:
            return default

        return json.loads(json_value)

    def get_assignment_variation(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: SubjectAttributes,
        default: Optional[ValueType],
        expected_variation_type: VariationType,
    ):
        try:
            result = self.get_assignment_detail(
                flag_key, subject_key, subject_attributes, expected_variation_type
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
        flag_key: str,
        subject_key: str,
        subject_attributes: SubjectAttributes,
        expected_variation_type: VariationType,
    ) -> FlagEvaluation:
        """Maps a subject to a variation for a given flag
        Returns None if the subject is not allocated in the flag

        :param subject_key: an identifier of the subject, for example a user ID.
        :param flag_key: a feature flag identifier
        :param subject_attributes: optional attributes associated with the subject, for example name and email.
        The subject attributes are used for evaluating any targeting rules tied
        to the flag and logged in the logging callback.
        """
        validate_not_blank("subject_key", subject_key)
        validate_not_blank("flag_key", flag_key)
        if subject_attributes is None:
            subject_attributes = {}

        flag = self.__config_requestor.get_configuration(flag_key)

        if flag is None:
            logger.warning(
                "[Eppo SDK] No assigned variation. Flag not found: " + flag_key
            )
            return none_result(
                flag_key, expected_variation_type, subject_key, subject_attributes
            )

        if not check_type_match(expected_variation_type, flag.variation_type):
            raise TypeError(
                f"Variation value does not have the correct type."
                f" Found: {flag.variation_type} != {expected_variation_type}"
            )

        if not flag.enabled:
            logger.info(
                "[Eppo SDK] No assigned variation. Flag is disabled: " + flag_key
            )
            return none_result(
                flag_key, expected_variation_type, subject_key, subject_attributes
            )

        result = self.__evaluator.evaluate_flag(flag, subject_key, subject_attributes)

        if result.variation and not check_value_type_match(
            expected_variation_type, result.variation.value
        ):
            logger.error(
                "[Eppo SDK] Variation value does not have the correct type for the flag: "
                f"{flag_key} and variation key {result.variation.key}"
            )
            return none_result(
                flag_key, flag.variation_type, subject_key, subject_attributes
            )

        assignment_event = {
            **(result.extra_logging if result else {}),
            "allocation": result.allocation_key if result else None,
            "experiment": f"{flag_key}-{result.allocation_key}" if result else None,
            "featureFlag": flag_key,
            "variation": result.variation.key if result and result.variation else None,
            "subject": subject_key,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "subjectAttributes": subject_attributes,
            "metaData": {"sdkLanguage": "python", "sdkVersion": __version__},
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

    def is_initialized(self):
        """
        Returns True if the client has successfully initialized
        the flag configuration and is ready to serve requests.
        """
        return self.__config_requestor.is_initialized()

    def _shutdown(self):
        """Stops all background processes used by the client
        Do not use the client after calling this method.
        """
        self.__poller.stop()


def check_type_match(
    expected_type: Optional[VariationType], actual_type: VariationType
):
    return expected_type is None or actual_type == expected_type


def check_value_type_match(
    expected_type: Optional[VariationType], value: ValueType
) -> bool:
    if expected_type is None:
        return True
    if expected_type in [VariationType.JSON, VariationType.STRING]:
        return isinstance(value, str)
    if expected_type == VariationType.INTEGER:
        return isinstance(value, int)
    if expected_type == VariationType.NUMERIC:
        # we can convert int to float
        return isinstance(value, float) or isinstance(value, int)
    if expected_type == VariationType.BOOLEAN:
        return isinstance(value, bool)
    return False
