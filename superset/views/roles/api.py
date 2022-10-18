from flask import Response, request
from flask_appbuilder.api import BaseApi, expose, safe

from superset import security_manager
from flask_jwt_extended.exceptions import NoAuthorizationError

from .utils import get_or_create_permission_view
from ..base_api import requires_json


class RoleRestApi(BaseApi):
    """ An api to get information about the current user """

    resource_name = "role"
    openapi_spec_tag = "Role"

    @expose("/name/<role_name>", methods=["GET"])
    @safe
    def get_by_name(self, role_name: int) -> Response:
        """
        Get the role object by name
        """
        try:
            role = security_manager.find_role(name=role_name)
            if role is None:
                return self.response_404()
        except NoAuthorizationError:
            return self.response_401()

        return self.response(200, result=role.to_json())

    @expose("/", methods=["POST"])
    @safe
    @requires_json
    def create(self) -> Response:
        """
        Create a new role
        """

        permission_view_objects = get_or_create_permission_view(request.json.pop("permission_view"))
        request.json["permissions"] = permission_view_objects

        try:
            role = security_manager.add_role(
                **request.json
            )
            if role is None:
                return self.response_400()
        except NoAuthorizationError:
            return self.response_401()

        return self.response(201, result=role.to_json())

    @expose("/name/<role_name>", methods=["DELETE"])
    @safe
    def delete(self, role_name) -> Response:
        """
        Delete role
        """
        try:
            role = security_manager.find_role(role_name)
            if not role:
                return self.response_404()
            is_deleted = security_manager.del_register_user(role)
            if not is_deleted:
                return self.response_500("Failed to delete Role")
        except NoAuthorizationError:
            return self.response_401()

        return self.response(204)

    @expose("/add_for_user", methods=["POST"])
    @safe
    @requires_json
    def add_for_user(self) -> Response:
        """
        Create a new role
        """
        user_id = request.json.pop("user_id", None)
        if not user_id:
            return self.response_404()

        user = security_manager.get_user_by_id(user_id)
        if user is None:
            return self.response_400()

        role_name = request.json.pop("role_name", None)
        if not role_name:
            return self.response_404()
        role = security_manager.find_role(name=role_name)
        if role is None:
            return self.response_400()

        try:
            user.roles.append(role)
            updated = security_manager.update_user(user)
            if updated is False:
                return self.response_500("Failed to add role to user")
        except NoAuthorizationError:
            return self.response_401()

        return self.response(200, result=role.to_json())

    @expose("/remove_from_user", methods=["POST"])
    @safe
    @requires_json
    def remove_from_user(self) -> Response:
        """
        Remove role from user
        """
        user_id = request.json.pop("user_id", None)
        if not user_id:
            return self.response_404()

        user = security_manager.get_user_by_id(user_id)
        if user is None:
            return self.response_400()

        role_name = request.json.pop("role_name", None)
        if not role_name:
            return self.response_404()
        role = security_manager.find_role(name=role_name)
        if role is None:
            return self.response_400()

        try:
            user.roles.remove(role)
            updated = security_manager.update_user(user)
            if updated is False:
                return self.response_500("Failed to remove role to user")
        except NoAuthorizationError:
            return self.response_401()

        return self.response(200, result=role.to_json())

    @expose("/add_permission_view", methods=["POST"])
    @safe
    @requires_json
    def add_permission_view(self) -> Response:
        """
        Remove role from user
        """
        permission_view_objects = get_or_create_permission_view(request.json.pop("permission_view"))

        role_name = request.json.pop("role_name", None)
        if not role_name:
            return self.response_404()
        role = security_manager.find_role(name=role_name)
        if role is None:
            return self.response_400()

        try:
            role.permissions.extend(permission_view_objects)
            security_manager.update_role(role.id, role_name)
        except NoAuthorizationError:
            return self.response_401()

        return self.response(200, result=role.to_json())

    @expose("/remove_permission_view", methods=["POST"])
    @safe
    @requires_json
    def remove_permission_view(self) -> Response:
        """
        Remove role from user
        """
        permission_view_objects = get_or_create_permission_view(
            request.json.pop("permission_view"))

        role_name = request.json.pop("role_name", None)
        if not role_name:
            return self.response_404()
        role = security_manager.find_role(name=role_name)
        if role is None:
            return self.response_400()

        try:
            for permission_view in permission_view_objects:
                role.permissions.remove(permission_view)
            security_manager.update_role(role.id, role_name)
        except NoAuthorizationError:
            return self.response_401()

        return self.response(200, result=role.to_json())
