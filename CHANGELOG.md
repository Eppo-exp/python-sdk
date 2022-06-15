<!---
## [MAJOR.MINOR.PATCH] - YYYY-MM-DD

#### New Features:
  * Describe any features added

#### Fixed:
  * Describe any bug fixes

#### Deprecated:
  * Describe deprecated APIs in this version
-->

## [1.0.0] - 2022-06-08

#### New Features:
* Subject attributes: an optional `subject_attributes` param is added to the `get_assignment` function. The subject attributes may contains custom metadata about the subject. These attributes are used for evaluating any targeting rules defined on the experiment.
```
client.get_assignment("<SUBJECT_KEY">, "<EXPERIMENT_KEY>", { "email": "user@example.com" });
```

#### Breaking Changes:
* The EppoClient `assign()` function is renamed to `get_assignment()`

## [0.0.3] - 2022-05-11

#### New Features
* Implemented allow list for subject-variation overrides