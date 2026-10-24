"""Private package holding the OpenAPI-generated Khipu clients.

Nothing under ``khipu_sdk._generated`` is a supported API: import only from
``khipu_sdk``. This file makes the generated clients a regular subpackage so
setuptools ships them inside the distribution. It is recreated deterministically
by ``make generate-all`` (see the ``ensure-generated-package`` target) so it
survives regeneration.

Do not add logic here. All hand-written code belongs in ``khipu_sdk``.
"""
