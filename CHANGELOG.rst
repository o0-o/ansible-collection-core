========================
o0\_o.core Release Notes
========================

.. contents:: Topics

v0.2.0
======

Release Summary
---------------

Major refactor of the command specification and processing
framework.  Adds effective user detection, removes default
stdout stripping, and introduces list expansion for dynamic
command generation.

Major Changes
-------------

- command_spec - Complete rewrite of process_command_spec with list expansion for dynamic command generation (cartesian product of list kwargs).
- command_utils - Refactored process_command_result to return flat dict with parsed/errors keys.  Added process_all_command_results for batch processing with type-based grouping.

Minor Changes
-------------

- command_spec - Renamed 'template' key to 'command' for clarity.
- command_utils - Added parser_kwargs and non_error_codes support in COMMAND_SPEC entries.
- core_action_base - Added _def_effective_user() method for determining the effective remote user (become-aware).

Breaking Changes / Porting Guide
--------------------------------

- command_spec - The 'template' key in COMMAND_SPEC entries has been renamed to 'command'.
- command_utils - process_command_result no longer strips trailing newlines or carriage returns from stdout. Stripping is now the parser's responsibility.  The no-parser default is true passthrough.
