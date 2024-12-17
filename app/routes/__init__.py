from flask import Flask
from .login_route import login_bp
from .account_route import account_bp




def register_routes(app: Flask):
    app.register_blueprint(login_bp)  
    app.register_blueprint(account_bp)



