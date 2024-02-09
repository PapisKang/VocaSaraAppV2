
from apps.api import blueprint
from flask_restx import Api

# from flask_restx import Api
api = Api(blueprint, title="API", description="API")

