from copy import copy

from django.db import models

from core.backends import get_backend
from core.exceptions import OriginalProviderLoginMissing

class AccountManager(models.Manager):
    """
    Manager for the Account model
    """

    def get_for_social_auth_user(self, social_auth_user):
        backend = social_auth_user.provider
        access_token = social_auth_user.extra_data.get('access_token', None)
        original_login = social_auth_user.extra_data.get('original_login', None)

        if not original_login:
            raise OriginalProviderLoginMissing(social_auth_user.user, backend)

        account = self.get_or_new(backend, original_login)
        account.access_token = access_token
        account.user = social_auth_user.user

        return account

    def get_or_new(self, backend, slug, **defaults):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        If defaults is given, it's content will be used to create the new Account
        """
        account = self.get_for_slug(backend, slug)
        if not account:
            defaults = copy(defaults)
            allowed_fields = self.model._meta.get_all_field_names()
            defaults = dict((key, value) for key, value in defaults.items()
                if key in allowed_fields)
            defaults['backend'] = backend
            defaults['slug'] = slug
            account = self.model(**defaults)
        return account

    def get_for_slug(self, backend, slug):
        """
        Try to return an existing account object for this backend/slug
        If not found, return None
        """
        try:
            return self.get(backend=backend, slug=slug)
        except:
            return None


class RepositoryManager(models.Manager):
    """
    Manager for the Repository model
    """

    def get_or_new(self, backend, project=None, **defaults):
        """
        Try to get a existing accout, else create one (without saving it in
        database)
        If the project is given, get params from it
        This way we can manage projects with user+slug or without user
        """
        backend = get_backend(backend)

        defaults = copy(defaults)

        # get params from the project name
        if project:
            identifiers = backend.parse_project(project)
            for identifier in backend.needed_repository_identifiers:
                if identifiers.get(identifier, False):
                    defaults[identifier] = identifiers[identifier]

        # test that we have all needed defaults
        backend.assert_valid_repository_identifiers(**defaults)

        try:
            identifiers = dict((key, defaults.get(key, None))
                for key in backend.needed_repository_identifiers)
            repository = self.get(**identifiers)
        except self.model.DoesNotExist:
            # remove empty defaults
            allowed_fields = self.model._meta.get_all_field_names()
            defaults = dict((key, value) for key, value in defaults.items()
                if key in allowed_fields)
            defaults['backend'] = backend.name

            repository = self.model(**defaults)

        return repository
