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

#### Breaking Changes:
* Subject attributes: the `subject` parameter of the assignment function was changed from a string to an object. The new `subject` object contains a `key` field for the subject ID as well as an optional `custom_attributes` property for any related metadata like name or email.

## [0.0.3] - 2022-05-11

#### New Features
* Implemented allow list for subject-variation overrides