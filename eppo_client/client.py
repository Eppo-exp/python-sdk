import datetime
import logging
import json
from typing import Any, Dict, Optional, Union
from eppo_client.assignment_logger import AssignmentLogger
from eppo_client.bandit import (
    ActionAttributes,
    BanditEvaluator,
    BanditResult,
    ContextAttributes,
    ActionContexts,
)
from eppo_client.models import Flag
from eppo_client.configuration_requestor import (
    ExperimentConfigurationRequestor,
)
from eppo_client.constants import POLL_INTERVAL_MILLIS, POLL_JITTER_MILLIS
from eppo_client.models import VariationType
from eppo_client.poller import Poller
from eppo_client.sharders import MD5Sharder
from eppo_client.types import Attributes, ValueType
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
        self.__bandit_evaluator = BanditEvaluator(sharder=MD5Sharder())

    def get_string_assignment(
        self,
        flag_key: str,
        subject_key: str,
        subject_attributes: Attributes,
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
        subject_attributes: Attributes,
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
        subject_attributes: Attributes,
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
        subject_attributes: Attributes,
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
        subject_attributes: Attributes,
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
        subject_attributes: Attributes,
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
        subject_attributes: Attributes,
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

    def get_bandit_action(
        self,
        flag_key: str,
        subject_key: str,
        subject_context: Union[ContextAttributes, Attributes],
        actions: Union[ActionContexts, ActionAttributes],
        default: str,
    ) -> BanditResult:
        """
        Determines the bandit action for a given subject based on the provided bandit key and subject attributes.

        This method performs the following steps:
        1. Retrieves the experiment assignment for the given bandit key and subject.
        2. Checks if the assignment matches the bandit key. If not, it means the subject is not allocated in the bandit,
           and the method returns a BanditResult with the assignment.
        3. If the subject is part of the bandit, it fetches the bandit model data.
        4. Evaluates the bandit action using the bandit evaluator.
        5. Logs the bandit action event.
        6. Returns the BanditResult containing the selected action key and the assignment.

        Args:
            flag_key (str): The feature flag key that contains the bandit as one of the variations.
            subject_key (str): The key identifying the subject.
            subject_context (ActionContexts | ActionAttributes): The subject context.
                If supplying an ActionAttributes, it gets converted to an ActionContexts instance
            actions (ActionContexts | ActionAttributes): The dictionary that maps action keys
                to their context of actions with their contexts.
                If supplying an ActionAttributes, it gets converted to an ActionContexts instance.
            default (str): The default variation to use if the subject is not part of the bandit.

        Returns:
            BanditResult: The result containing either the bandit action if the subject is part of the bandit,
                          or the assignment if they are not. The BanditResult includes:
                          - variation (str): The assignment key indicating the subject's variation.
                          - action (str): The key of the selected action if the subject is part of the bandit.

        Example:
        result = client.get_bandit_action(
            "flag_key",
            "subject_key",
            ContextAttributes(
                numeric_attributes={"age": 25},
                categorical_attributes={"country": "USA"}),
            {
                "action1": ContextAttributes(
                    numeric_attributes={"price": 10.0},
                    categorical_attributes={"category": "A"}
                ),
                "action2": {"price": 10.0, "category": "B"}
                "action3": ContextAttributes.empty(),
            },
            "default"
        )
        if result.action is None:
            do_variation(result.variation)
        else:
            do_action(result.action)
        """
        try:
            return self.get_bandit_action_detail(
                flag_key,
                subject_key,
                subject_context,
                actions,
                default,
            )
        except Exception as e:
            if self.__is_graceful_mode:
                logger.error("[Eppo SDK] Error getting bandit action: " + str(e))
                return BanditResult(default, None)
            raise e

    def get_bandit_action_detail(
        self,
        flag_key: str,
        subject_key: str,
        subject_context: Union[ContextAttributes, Attributes],
        actions: Union[ActionContexts, ActionAttributes],
        default: str,
    ) -> BanditResult:
        subject_attributes = convert_subject_context_to_attributes(subject_context)
        action_contexts = convert_actions_to_action_contexts(actions)

        # get experiment assignment
        # ignoring type because Dict[str, str] satisfies Dict[str, str | ...] but mypy does not understand
        variation = self.get_string_assignment(
            flag_key,
            subject_key,
            subject_attributes.categorical_attributes
            | subject_attributes.numeric_attributes,  # type: ignore
            default,
        )

        # if the variation is not the bandit key, then the subject is not allocated in the bandit
        if variation not in self.get_bandit_keys():
            return BanditResult(variation, None)

        # for now, assume that the variation is equal to the bandit key
        bandit_data = self.__config_requestor.get_bandit_model(variation)

        if not bandit_data:
            logger.warning(
                f"[Eppo SDK] No assigned action. Bandit not found for flag: {flag_key}"
            )
            return BanditResult(variation, None)

        evaluation = self.__bandit_evaluator.evaluate_bandit(
            flag_key,
            subject_key,
            subject_attributes,
            action_contexts,
            bandit_data.model_data,
        )

        # log bandit action
        bandit_event = {
            "flagKey": flag_key,
            "banditKey": bandit_data.bandit_key,
            "subject": subject_key,
            "action": evaluation.action_key if evaluation else None,
            "actionProbability": evaluation.action_weight if evaluation else None,
            "optimalityGap": evaluation.optimality_gap if evaluation else None,
            "modelVersion": bandit_data.model_version if evaluation else None,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "subjectNumericAttributes": (
                subject_attributes.numeric_attributes
                if evaluation.subject_attributes
                else {}
            ),
            "subjectCategoricalAttributes": (
                subject_attributes.categorical_attributes
                if evaluation.subject_attributes
                else {}
            ),
            "actionNumericAttributes": (
                evaluation.action_attributes.numeric_attributes
                if evaluation.action_attributes
                else {}
            ),
            "actionCategoricalAttributes": (
                evaluation.action_attributes.categorical_attributes
                if evaluation.action_attributes
                else {}
            ),
            "metaData": {"sdkLanguage": "python", "sdkVersion": __version__},
        }
        self.__assignment_logger.log_bandit_action(bandit_event)

        return BanditResult(variation, evaluation.action_key if evaluation else None)

    def get_flag_keys(self):
        """
        Returns a list of all flag keys that have been initialized.
        This can be useful to debug the initialization process.

        Note that it is generally not a good idea to pre-load all flag configurations.
        """
        return self.__config_requestor.get_flag_keys()

    def get_flag_configurations(self) -> Dict[str, Flag]:
        """
        Returns a dictionary of all flag configurations that have been initialized.
        This can be useful to debug the initialization process or to bootstrap a front-end client.
        """
        return self.__config_requestor.get_flag_configurations()

    def get_bandit_keys(self):
        """
        Returns a list of all bandit keys that have been initialized.
        This can be useful to debug the initialization process.
        """
        return self.__config_requestor.get_bandit_keys()

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


def convert_subject_context_to_attributes(
    subject_context: Union[ContextAttributes, Attributes]
) -> ContextAttributes:
    if isinstance(subject_context, dict):
        return ContextAttributes.from_dict(subject_context)
    return subject_context


def convert_actions_to_action_contexts(
    actions: Union[ActionContexts, ActionAttributes]
) -> ActionContexts:
    return {
        k: ContextAttributes.from_dict(v) if isinstance(v, dict) else v
        for k, v in actions.items()
    }
