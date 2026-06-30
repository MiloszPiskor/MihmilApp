from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask import g, abort
from domain import model

class SecureModelView(ModelView):
    def is_accessible(self):
        user = getattr(g, "current_user", None)
        return bool(user and user.role == "admin")

    def inaccessible_callback(self, name, **kwargs):
        abort(403)

class UserAdminView(SecureModelView):
    column_list = ("sub", "email", "name", "role", "rep_reference", "is_active")
    column_editable_list = ("role", "rep_reference", "is_active")
    form_excluded_columns = ("sub",)
    can_create = False

class SalesRepAdminView(SecureModelView):
    column_list = ("reference", "name", "email")
    form_columns = ("reference", "name", "email")

class CompanyAdminView(SecureModelView):
    column_list = ("nip", "name", "ltd", "city", "postal_code", "street", "building_nr", "version")
    form_columns = ("nip", "name", "ltd", "street", "building_nr", "postal_code", "city", "version")

def setup_admin(app, session):
    admin = Admin(app, name="Internal Admin", template_mode="bootstrap4", url="/admin")
    admin.add_view(UserAdminView(model.User, session))
    admin.add_view(SalesRepAdminView(model.SalesRep, session))
    admin.add_view(CompanyAdminView(model.Company, session))
    return admin
