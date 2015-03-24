from django.shortcuts import get_object_or_404

from rest_framework.generics import (ListCreateAPIView, RetrieveAPIView,
                                     RetrieveUpdateDestroyAPIView)

from common.mixins import NeverCacheMixin
from common.permissions import HasValidToken


class UserDataMixin(object):
    """
    A mixin that handles getting the UserData for a given user and access
    token.
    """

    def get_user_data_related_name(self):
        """
        Return the related_name of the UserData model in relation to the User
        model, e.g. american_gut, go_viral, pgp
        """
        return self.user_data_model.user.field.related_query_name()

    def get_user_data(self):
        """
        A helper function to retrieve the given study's UserData model that
        corresponds to the request user.
        """
        # We get the UserData object this way because if we try to do it via a
        # filter the object will not be automatically created (it's an
        # AutoOneToOneField and so is only created when accessed like
        # `user.american_gut`)
        return getattr(self.request.user, self.get_user_data_related_name())

    def get_user_data_queryset(self):
        """
        A helper function to retrieve the given study's UserData model as a
        pre-filtered queryset that corresponds to the request user.
        """
        # HACK: A side effect of this call is that the UserData object will be
        # created if it doesn't exist... Which is useful for the next line,
        # which filters by it.
        self.get_user_data()

        return self.user_data_model.objects.filter(user=self.request.user)

    # TODO: Add scope permissions here?
    def get_object(self):
        """
        Get an object from its `pk`.
        """
        filters = {}

        # There's only one UserData for a given user so we don't need to filter
        # for it. We set its lookup_field to None for this reason.
        if self.lookup_field:
            filters[self.lookup_field] = self.kwargs[self.lookup_field]

        obj = get_object_or_404(self.get_queryset(), **filters)

        self.check_object_permissions(self.request, obj)

        return obj

    def perform_create(self, serializer):
        """
        perform_create is called when models are saved. We add in the user_data
        here so that on model creation it's set correctly.
        """
        serializer.save(user_data=self.get_user_data())


class UserDataDetailView(NeverCacheMixin, UserDataMixin, RetrieveAPIView):
    """
    A read-only detail view for a study's UserData object.
    """
    lookup_field = None
    permission_classes = (HasValidToken,)


class StudyDetailView(NeverCacheMixin, UserDataMixin,
                      RetrieveUpdateDestroyAPIView):
    """
    A detail view that can be GET, PUT, DELETEd.
    """
    permission_classes = (HasValidToken,)


class RetrieveStudyDetailView(NeverCacheMixin, UserDataMixin, RetrieveAPIView):
    """
    A detail view that can be GET.
    """
    permission_classes = (HasValidToken,)


class StudyListView(NeverCacheMixin, UserDataMixin, ListCreateAPIView):
    """
    A list view that can be GET or POSTed.
    """
    permission_classes = (HasValidToken,)
