from flask import Response, request
from flask_appbuilder.api import BaseApi, expose, safe

from superset import security_manager
from flask_jwt_extended.exceptions import NoAuthorizationError

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
        permission_view_names = request.json.pop("permission_view")
        if permission_view_names:
            permission_view_names = permission_view_names if isinstance(permission_view_names, list) else [permission_view_names]

        permission_view_objects = []
        for permission_name, view_name in permission_view_names:

            permission_view_obj = security_manager.find_permission_view_menu(permission_name, view_name)
            if not permission_view_obj:
                permission_view_obj = security_manager.add_permission_view_menu(
                    permission_name, view_name)
            permission_view_objects.append(permission_view_obj)

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
