from typing import Tuple, List

from superset import security_manager


def get_or_create_permission_view(permission_view_names: [List[Tuple], Tuple]):
    if permission_view_names:
        permission_view_names = permission_view_names if isinstance(
            permission_view_names, list) else [permission_view_names]

    permission_view_objects = []
    for permission_name, view_name in permission_view_names:

        permission_view_obj = security_manager.find_permission_view_menu(
            permission_name, view_name)
        if not permission_view_obj:
            permission_view_obj = security_manager.add_permission_view_menu(
                permission_name, view_name)
        permission_view_objects.append(permission_view_obj)

    return permission_view_objects

