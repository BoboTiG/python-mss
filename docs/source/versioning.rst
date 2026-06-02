Versioning
==========

This document describes how changes are managed across MSS releases and
what users can expect when upgrading.

MSS follows `Semantic Versioning <https://semver.org/>`_ (SemVer) with
additional conventions described below.

These guidelines describe how changes are managed and reflect the
project's intent. They are not a guarantee of behavior in all cases.

Overview
--------

MSS version numbers follow the format :samp:`{major}.{minor}.{patch}`:

- **Major versions** introduce backward-incompatible changes.
- **Minor versions** add new features or improvements without breaking
  existing documented usage.
- **Patch versions** fix bugs and do not intentionally change the public
  API.

Patch and minor releases are intended to be backward-compatible with
previous releases of the same major version. If a regression occurs, it
is treated as a defect.

Public API
----------

The public API consists of:

- Features documented in the official documentation (Sphinx docs built
  from :file:`docs/`), unless explicitly marked otherwise
- Features demonstrated in official examples (:file:`docs/source/examples/`)
  or demos (:file:`demos/`), unless explicitly marked otherwise

Examples and demos are intended to show recommended usage patterns and
are considered part of the public surface that users may reasonably rely
on.

The following are **not** considered part of the public API:

- Undocumented symbols
- Internal modules or backend-specific implementation details
- Docstrings (which may reference internal behavior and are not yet
  fully audited)

Some currently accessible symbols may still be internal even if not
prefixed with :code:`_`. These should not be relied upon and may change
without notice.

Compatibility Rules
-------------------

The following describes how changes are generally handled across
versions.

Changes That Require a Major Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following changes are treated as backward-incompatible:

- Removing public API symbols (functions, classes, attributes, etc.)
- Removing keyword parameters
- Making function arguments more restrictive than documented
- Returning values outside documented types
- Raising exceptions in cases where behavior was previously documented
  or clearly implied to succeed
- Removing support for Python or operating system versions

Changes That Do Not Require a Major Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following changes are considered backward-compatible:

- Adding new optional or keyword parameters
- Adding new functions, attributes, or data fields
- Widening accepted parameter types
- Narrowing return types within documented bounds
- Raising exceptions for previously undefined or invalid inputs
- Emitting or modifying warnings
- Returning subclasses where a base class was previously returned
- Changing exception messages (exception types remain stable)

Deprecation Policy
------------------

When a feature is planned for removal:

- It is typically deprecated in a minor release before removal in a
  future major release
- Deprecation notices are included in the documentation and release
  notes
- :py:class:`DeprecationWarning` may be emitted where practical

In some cases, deprecated features may be removed from documentation
before being removed from the code.

Feature Gating
--------------

New functionality may be introduced behind explicit user opt-in
mechanisms ("feature gates").

Behavior enabled only through an explicit opt-in is not considered a
breaking change.

Hypothetical example of a gated feature::

   with MSS() as sct:
       img = sct.grab(sct.primary_monitor)
       # returns ScreenShotCPU

   with MSS(device="cuda") as sct:
       img = sct.grab(sct.primary_monitor)
       # returns ScreenShotCUDA

Because the new behavior is only enabled when explicitly requested, it
does not affect existing usage.

Typing and Compatibility
------------------------

Type annotations may evolve across major versions.

In some cases, type changes may occur that do not affect runtime
behavior but may require updates for static type checking tools.

When evaluating such changes, considerations include:

- Likelihood of affecting real-world usage
- Difficulty of adapting existing code
- Overall benefit to the ecosystem

Runtime compatibility is generally prioritized over strict type
stability.

In some limited cases, MSS may widen type annotations in a minor
release to support a new feature that is only available through
explicit user opt-in. This is only considered for gated features where
the runtime behavior of existing code does not change and where
type-checking support is added so that static analysis can still infer
the narrower type in ordinary usage.

For example, this may be appropriate when overloads, generics, or other
typing features allow type checkers to determine the correct return type
based on the user's explicit configuration. MSS may use this approach
when it is expected to avoid type-checking impact for the vast majority
of users and when the added feature is important enough to justify the
change.

Stability Guidelines
--------------------

MSS aims to preserve documented behavior across releases. This includes
the meaning of documented APIs, arguments, return values, and data
fields.

Behavior that is undocumented, incidental, or implementation-specific
should not be relied upon and may change between releases.

Internal strategies, backend selection, validation details, error
messages, and other implementation details are not considered stable
unless explicitly documented.

Widely used features receive greater stability consideration than niche
or specialized functionality.

Writing Forward-Compatible Code
-------------------------------

To minimize disruption when upgrading:

- Use documented public APIs only
- Avoid relying on internal modules or backend-specific behavior
- Prefer explicit, documented interfaces over implicit conventions
- Expect stricter validation of inputs over time

Undocumented behavior should not be relied upon and may change without
notice.

Philosophy
----------

MSS aims to be:

- Easy to use for programmers of all experience levels
- Suitable for a wide range of projects

Changes are made carefully, with the goal of improving functionality,
performance, and maintainability while minimizing disruption.

When breaking changes are necessary, they are introduced deliberately
and with advance notice where practical.

Where possible, compatibility layers may be provided to allow existing
code to continue working during transitions.
