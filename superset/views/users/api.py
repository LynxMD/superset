# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from flask import g, Response, request
from flask_appbuilder.api import BaseApi, expose, safe
from flask_appbuilder.security.decorators import protect

from superset import security_manager
from flask_jwt_extended.exceptions import NoAuthorizationError

from .schemas import UserResponseSchema
from ..base_api import requires_json

user_response_schema = UserResponseSchema()


class CurrentUserRestApi(BaseApi):
    """ An api to get information about the current user """

    resource_name = "me"
    openapi_spec_tag = "Current User"
    openapi_spec_component_schemas = (UserResponseSchema,)

    @expose("/", methods=["GET"])
    @safe
    def get_me(self) -> Response:
        """Get the user object corresponding to the agent making the request
        ---
        get:
          description: >-
            Returns the user object corresponding to the agent making the request,
            or returns a 401 error if the user is unauthenticated.
          responses:
            200:
              description: The current user
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      result:
                        $ref: '#/components/schemas/UserResponseSchema'
            401:
              $ref: '#/components/responses/401'
        """
        try:
            if g.user is None or g.user.is_anonymous:
                return self.response_401()
        except NoAuthorizationError:
            return self.response_401()

        return self.response(200, result=user_response_schema.dump(g.user))


class UserRestApi(BaseApi):
    """ An api to get information about the current user """

    resource_name = "user"
    openapi_spec_tag = "User"
    openapi_spec_component_schemas = (UserResponseSchema,)

    @expose("/<email>", methods=["GET"])
    @safe
    def get_by_email(self, email: int) -> Response:
        """
        Get the user object by email
        """
        try:
            user = security_manager.find_user(email=email)
            if user is None:
                return self.response_401()
        except NoAuthorizationError:
            return self.response_401()

        return self.response(200, result=user_response_schema.dump(user))

    @expose("/", methods=["POST"])
    @protect()
    @safe
    @requires_json
    def create(self) -> Response:
        """
        Create a new user
        """
        try:
            user = security_manager.add_user(
                **request.json
            )
            if user is False:
                return self.response_400()
        except NoAuthorizationError:
            return self.response_401()

        return self.response(201, result=user_response_schema.dump(user))

    @expose("/<user_id>", methods=["DELETE"])
    @protect()
    @safe
    def delete(self, user_id) -> Response:
        """
        Delete user
        """
        try:
            user = security_manager.get_user_by_id(user_id)
            if not user:
                return self.response_404()
            is_deleted = security_manager.del_register_user(user)
            if not is_deleted:
                return self.response_500("Failed to delete user")
        except NoAuthorizationError:
            return self.response_401()

        return self.response(204)
